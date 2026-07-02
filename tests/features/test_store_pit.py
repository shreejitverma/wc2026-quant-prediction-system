"""PIT invariant on the DuckDB feature store.

These tests are the persistent-store analogue of tests/test_pit.py.
They prove that `FeatureStore.get_features(match_id, as_of_ts)` can never
return a feature whose `knowable_at > as_of_ts`, regardless of what is in the
database. The Hypothesis-based property test runs hundreds of random scenarios.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wc2026.features.store import FeatureStore

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _dt(days: float) -> datetime:
    return _BASE + timedelta(days=days)


# --- Unit tests ---

def test_basic_write_and_read(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(0))
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(1))
        assert row["elo_home"] == pytest.approx(1943.0)


def test_future_feature_not_returned(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        # Feature knowable at day 5 — should not appear if queried at day 3
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(5))
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(3))
        assert "elo_home" not in row


def test_exact_boundary_is_included(tmp_path):
    """knowable_at == as_of_ts: the feature IS admissible (non-strict <=)."""
    ts = _dt(3)
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=ts)
        row = fs.get_features("MEX-ENG", as_of_ts=ts)
        assert "elo_home" in row


def test_latest_revision_wins(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1900.0, knowable_at=_dt(0))
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(1))
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(2))
        assert row["elo_home"] == pytest.approx(1943.0)


def test_old_revision_visible_at_old_cutoff(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1900.0, knowable_at=_dt(0))
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(5))
        # At day 3, only the day-0 value is admissible
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(3))
        assert row["elo_home"] == pytest.approx(1900.0)


def test_different_matches_isolated(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(0))
        fs.upsert("BRA-FRA", "elo_home", 2031.0, knowable_at=_dt(0))
        r1 = fs.get_features("MEX-ENG", as_of_ts=_dt(1))
        r2 = fs.get_features("BRA-FRA", as_of_ts=_dt(1))
        assert r1["elo_home"] == pytest.approx(1943.0)
        assert r2["elo_home"] == pytest.approx(2031.0)


def test_string_feature_stored_and_retrieved(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "stage", "Round of 32", knowable_at=_dt(0))
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(1))
        assert row["stage"] == "Round of 32"


def test_none_value_not_retrieved(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "rest_days", None, knowable_at=_dt(0))
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(1))
        # None values produce a row with both value_num and value_str null
        # get_features returns None or omits the key — either is acceptable
        assert row.get("rest_days") is None


def test_upsert_many(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert_many(
            "MEX-ENG",
            {"elo_home": 1943.0, "elo_away": 2046.0, "neutral": 1.0},
            knowable_at=_dt(0),
        )
        row = fs.get_features("MEX-ENG", as_of_ts=_dt(1))
        assert row["elo_home"] == pytest.approx(1943.0)
        assert row["elo_away"] == pytest.approx(2046.0)
        assert row["neutral"] == pytest.approx(1.0)


def test_row_count(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert_many("A", {"x": 1.0, "y": 2.0}, knowable_at=_dt(0))
        fs.upsert_many("B", {"x": 3.0}, knowable_at=_dt(0))
        assert fs.row_count() == 3


def test_export_parquet(tmp_path):
    with FeatureStore(tmp_path / "f.duckdb") as fs:
        fs.upsert("MEX-ENG", "elo_home", 1943.0, knowable_at=_dt(0))
        out = tmp_path / "features.parquet"
        fs.export_parquet(out)
        assert out.exists()
        assert out.stat().st_size > 0


# --- Property-based test: the PIT invariant on the persistent store ---

_days = st.floats(min_value=0.0, max_value=365.0)
_feat_batches = st.lists(
    st.tuples(st.text(min_size=1, max_size=6), _days, st.floats(min_value=-1000, max_value=5000)),
    max_size=30,
)


@given(batches=_feat_batches, query_days=_days)
def test_no_future_feature_ever_leaks_from_store(batches, query_days):
    """Property: get_features(as_of_ts=Q) never returns a feature with knowable_at > Q."""
    q_ts = _dt(query_days)
    with tempfile.TemporaryDirectory() as tmpdir:
        with FeatureStore(Path(tmpdir) / "f.duckdb") as fs:
            for feat_name, ka_days, value in batches:
                fs.upsert("MATCH", feat_name, value, knowable_at=_dt(ka_days))
            result = fs.get_features("MATCH", as_of_ts=q_ts)

    # Every returned feature must have been knowable at or before the query time.
    # We verify this by checking that all returned names correspond to records
    # where ka_days <= query_days. Since the store enforces this in SQL, this
    # test is a regression guard: if someone modifies the SQL query to remove
    # the WHERE clause, this test will catch it.
    # Compare as datetimes (not raw floats) to match DuckDB's microsecond precision.
    # Sub-microsecond float differences (e.g. 3e-229 days) round to zero in timedelta.
    admissible_names = {
        feat_name
        for feat_name, ka_days, _ in batches
        if _dt(ka_days) <= q_ts
    }
    for returned_name in result:
        assert returned_name in admissible_names, (
            f"Feature '{returned_name}' was returned but should not be admissible "
            f"at query_days={query_days:.3f}"
        )
