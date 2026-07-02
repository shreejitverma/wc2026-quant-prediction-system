"""Phase 0 end-to-end smoke test: exercises the honesty harness for real.

Run with `make selfcheck` (or `uv run python scripts/phase0_selfcheck.py`). It
loads config, drives the point-in-time gate, writes and verifies a hash-chained
ledger, logs a reproducible run, and queries the ledger through DuckDB - proving
the whole Phase 0 stack works together, not just in unit isolation.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb

from wc2026.config import config_hash, load_config
from wc2026.ledger import AppendOnlyLedger
from wc2026.pit import PointInTimeStore
from wc2026.runs import log_run

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def main() -> int:
    # 1) Config loads and hashes.
    cfg = load_config(REPO_ROOT / "configs" / "default.yaml")
    _ok(f"config loaded (mode={cfg.mode}) hash={config_hash(cfg)[:12]}")

    # 2) Point-in-time gate: a lineup fact is invisible before it is knowable.
    kickoff = datetime(2026, 6, 11, 18, 0, 0, tzinfo=UTC)
    lineup_release = kickoff - timedelta(minutes=70)
    store: PointInTimeStore[str] = PointInTimeStore()
    store.add_value("lineup:MEX", lineup_release, "starting_xi_v1")
    before = store.as_of(lineup_release - timedelta(minutes=1), "lineup:MEX")
    after = store.as_of(lineup_release, "lineup:MEX")
    assert before == [] and len(after) == 1
    _ok("point-in-time gate hides the lineup until its release timestamp")

    with tempfile.TemporaryDirectory() as d:
        # 3) Append-only, hash-chained ledger + tamper detection.
        led = AppendOnlyLedger(Path(d) / "ledger.jsonl")
        led.append("prediction", {"match": "MEX-CAN", "p_home": 0.42}, ts=kickoff)
        led.append("quote", {"contract": "MEX_WIN", "bid": 0.40, "ask": 0.44}, ts=kickoff)
        assert led.verify_chain()
        _ok(f"ledger chain verified over {len(led)} entries")

        # 4) Reproducible run record.
        runs = AppendOnlyLedger(Path(d) / "runs.jsonl")
        rec = log_run(
            runs,
            config=cfg,
            model_name="M1_dixon_coles",
            model_version="0.0.1",
            metrics={"log_loss": 0.98},
            repo=REPO_ROOT,
        )
        assert runs.verify_chain()
        _ok(f"run logged (run_id={rec.run_id[:8]}, dirty={rec.git_dirty})")

        # 5) DuckDB reads the JSONL ledger (proves the query engine choice works).
        con = duckdb.connect()
        n = con.execute(
            "SELECT count(*) FROM read_json_auto(?, format='newline_delimited')",
            [str(Path(d) / "ledger.jsonl")],
        ).fetchone()[0]
        assert n == 2
        _ok(f"duckdb queried the ledger ({n} rows)")

    print("\nPhase 0 self-check: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
