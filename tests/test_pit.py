"""Property-based proof of the leakage gate.

These tests are the enforcement mechanism behind Decision 1. They are also wired
into pre-commit (see .pre-commit-config.yaml): a change that lets a future fact
leak through `as_of` cannot be committed. This is the "prove it with tests, not
promises" requirement made literal.
"""

from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wc2026.pit import PointInTimeStore

# Epoch seconds in a plausible range; converted to tz-aware UTC datetimes.
_epoch = st.integers(min_value=0, max_value=2_000_000_000)
_records = st.lists(
    st.tuples(st.text(min_size=1, max_size=4), _epoch, st.integers()),
    max_size=50,
)


def _dt(e: int) -> datetime:
    return datetime.fromtimestamp(e, tz=UTC)


@given(recs=_records, q=_epoch)
def test_no_future_fact_ever_leaks(recs, q):
    store: PointInTimeStore[int] = PointInTimeStore()
    for key, e, v in recs:
        store.add_value(key, _dt(e), v)

    q_ts = _dt(q)
    got = store.as_of(q_ts)

    # Invariant 1: nothing knowable *after* the cutoff is returned.
    assert all(r.knowable_at <= q_ts for r in got)
    # Invariant 2: nothing knowable *at or before* the cutoff is dropped.
    expected = sum(1 for _, e, _ in recs if e <= q)
    assert len(got) == expected


@given(recs=_records, q=_epoch)
def test_latest_is_the_most_recent_admissible(recs, q):
    store: PointInTimeStore[int] = PointInTimeStore()
    for key, e, v in recs:
        store.add_value(key, _dt(e), v)
    q_ts = _dt(q)

    for key in {k for k, _, _ in recs}:
        latest = store.latest(q_ts, key)
        admissible = store.as_of(q_ts, key)
        if not admissible:
            assert latest is None
        else:
            assert latest is not None
            assert latest.knowable_at == max(r.knowable_at for r in admissible)


def test_pit_rejects_naive_timestamp():
    store: PointInTimeStore[int] = PointInTimeStore()
    with pytest.raises(ValueError):
        store.add_value("k", datetime(2026, 6, 11, 18, 0, 0), 1)  # naive
