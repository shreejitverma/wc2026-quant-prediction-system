"""DuckDB-backed, point-in-time-correct feature store.

Design:
  - One DuckDB database file (`features.duckdb`) with an append-only
    `features` table. Each row is one (match_id, feature_name, value,
    knowable_at) tuple.
  - `upsert()` adds or replaces a feature value; the old row is not deleted
    but tagged `superseded=true`. The latest non-superseded row wins.
  - `get_features(match_id, as_of_ts)` returns only rows where
    `knowable_at <= as_of_ts AND superseded=false`.
  - The WHERE clause is the enforcement mechanism; there is no code path
    that bypasses it.

Why one table rather than one file per feature family:
  - Simpler to add new feature families without schema migrations.
  - DuckDB handles columnar scans efficiently even on a wide FILTER.
  - A Parquet export of the full table is trivial for archiving.

Numeric values are stored as DOUBLE. String/categorical values are stored as
JSON in `value_str`. Both may be non-null simultaneously only for debug; code
always reads from the typed column it wrote to.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from ..time_utils import ensure_utc, to_iso, utc_now

_SCHEMA = """
CREATE TABLE IF NOT EXISTS features (
    match_id      VARCHAR NOT NULL,
    feature_name  VARCHAR NOT NULL,
    value_num     DOUBLE,
    value_str     VARCHAR,
    knowable_at   TIMESTAMP NOT NULL,
    written_at    TIMESTAMP NOT NULL,
    superseded    BOOLEAN NOT NULL DEFAULT false,
    source        VARCHAR DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_features_lookup
    ON features (match_id, feature_name, knowable_at, superseded);
"""

_UPSERT = """
UPDATE features
SET superseded = true
WHERE match_id = ? AND feature_name = ? AND superseded = false;

INSERT INTO features
    (match_id, feature_name, value_num, value_str, knowable_at, written_at, source)
VALUES (?, ?, ?, ?, ?, ?, ?);
"""

_QUERY = """
SELECT
    feature_name,
    value_num,
    value_str,
    knowable_at
FROM features
WHERE match_id = ?
  AND knowable_at <= ?::TIMESTAMP
  AND superseded = false
ORDER BY feature_name, knowable_at DESC
"""


class FeatureStore:
    """The single sanctioned access path for all features.

    Usage:
        fs = FeatureStore("data/processed/features.duckdb")
        fs.upsert("MEX-ENG-20260705", "elo_home", 1943.0, knowable_at=ts)
        row = fs.get_features("MEX-ENG-20260705", as_of_ts=ts)
        # row["elo_home"] -> 1943.0
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(str(self.db_path))
        self._con.execute(_SCHEMA)

    def upsert(
        self,
        match_id: str,
        feature_name: str,
        value: float | str | None,
        *,
        knowable_at: datetime,
        source: str = "",
    ) -> None:
        """Write or replace a feature value for a match.

        If the feature already exists (same match_id + feature_name), the old
        row is marked superseded and a new row is inserted. This preserves
        history for audit while `get_features` always sees only the latest.
        """
        ka = ensure_utc(knowable_at)
        wa = utc_now()
        value_num = float(value) if isinstance(value, (int, float)) else None
        value_str = value if isinstance(value, str) else (
            json.dumps(value) if value is not None and value_num is None else None
        )
        # Only supersede rows with the EXACT same knowable_at (corrections).
        # Rows at different knowable_at must remain visible for PIT queries
        # at intermediate timestamps.
        self._con.execute(
            "UPDATE features SET superseded=true "
            "WHERE match_id=? AND feature_name=? AND knowable_at=?::TIMESTAMP AND superseded=false",
            [match_id, feature_name, to_iso(ka)],
        )
        self._con.execute(
            "INSERT INTO features "
            "(match_id,feature_name,value_num,value_str,knowable_at,written_at,source) "
            "VALUES (?,?,?,?,?,?,?)",
            [match_id, feature_name, value_num, value_str,
             to_iso(ka), to_iso(wa), source],
        )

    def upsert_many(
        self,
        match_id: str,
        features: dict[str, float | str | None],
        *,
        knowable_at: datetime,
        source: str = "",
    ) -> None:
        """Write a batch of features for one match in one transaction."""
        with self._con.cursor() as cur:
            cur.execute("BEGIN")
            try:
                for name, value in features.items():
                    self.upsert(match_id, name, value,
                                knowable_at=knowable_at, source=source)
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def get_features(self, match_id: str, as_of_ts: datetime) -> dict[str, Any]:
        """Return all features for match_id knowable at or before as_of_ts.

        This is the ONLY read path. The WHERE clause is the PIT gate.
        Returns {feature_name: value} using value_num if set, else value_str.
        When multiple revisions exist for the same feature (should be rare),
        only the latest knowable_at is returned.
        """
        ts = ensure_utc(as_of_ts)
        rows = self._con.execute(_QUERY, [match_id, to_iso(ts)]).fetchall()

        result: dict[str, Any] = {}
        seen: set[str] = set()
        for feature_name, value_num, value_str, _ in rows:
            if feature_name in seen:
                continue  # ORDER BY knowable_at DESC so first seen = latest
            seen.add(feature_name)
            if value_num is not None:
                result[feature_name] = value_num
            elif value_str is not None:
                try:
                    result[feature_name] = json.loads(value_str)
                except json.JSONDecodeError:
                    result[feature_name] = value_str
        return result

    def feature_names(self, match_id: str | None = None) -> list[str]:
        """All distinct feature names in the store (optionally for one match)."""
        if match_id:
            rows = self._con.execute(
                "SELECT DISTINCT feature_name FROM features WHERE match_id=? AND superseded=false",
                [match_id],
            ).fetchall()
        else:
            rows = self._con.execute(
                "SELECT DISTINCT feature_name FROM features WHERE superseded=false"
            ).fetchall()
        return sorted(r[0] for r in rows)

    def match_ids(self) -> list[str]:
        rows = self._con.execute(
            "SELECT DISTINCT match_id FROM features WHERE superseded=false"
        ).fetchall()
        return sorted(r[0] for r in rows)

    def row_count(self) -> int:
        return self._con.execute(
            "SELECT count(*) FROM features WHERE superseded=false"
        ).fetchone()[0]

    def export_parquet(self, path: str | Path) -> None:
        """Export the active (non-superseded) feature table to Parquet for archiving."""
        self._con.execute(
            f"COPY (SELECT * FROM features WHERE superseded=false) "
            f"TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> FeatureStore:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
