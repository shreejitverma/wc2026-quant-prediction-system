"""Bootstrap real data/ artifacts so the API's real endpoints have something
genuine to serve.

This writes only records of events that actually happened - it fabricates no
model output:
  - data/ledger/ledger.jsonl : one kind="ops" entry recording this bootstrap.
  - data/runs/runs.jsonl     : one genuine RunRecord (model_name="api-smoke")
    whose notes state explicitly that no model was fitted. Its git commit,
    dirty flag, and config hash are real provenance of this working tree.

Idempotent by default: if the main ledger already has entries, it does nothing
(the ledger is append-only; re-running with --force appends a new ops event,
it never rewrites).

Usage: uv run python scripts/bootstrap_api_data.py [--force]
"""

from __future__ import annotations

import sys
from pathlib import Path

from wc2026.config import config_hash, load_config
from wc2026.ledger import AppendOnlyLedger
from wc2026.runs import log_run

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    force = "--force" in sys.argv[1:]
    cfg = load_config(REPO_ROOT / "configs" / "default.yaml")

    ledger = AppendOnlyLedger(REPO_ROOT / cfg.paths.ledger_dir / "ledger.jsonl")
    if len(ledger) > 0 and not force:
        print(f"[SKIP] ledger already has {len(ledger)} entries (use --force to append anyway)")
        return 0

    entry = ledger.append(
        kind="ops",
        payload={
            "event": "api_bootstrap",
            "detail": "API layer bootstrapped; ledger and runs artifacts created.",
            "config_hash": config_hash(cfg),
            "mode": cfg.mode,
        },
    )
    print(f"[OK] ledger entry seq={entry['seq']} row_hash={entry['row_hash'][:12]}")

    runs_ledger = AppendOnlyLedger(REPO_ROOT / cfg.paths.runs_dir / "runs.jsonl")
    rec = log_run(
        runs_ledger,
        config=cfg,
        model_name="api-smoke",
        model_version="0.0.0",
        metrics={},
        notes=(
            "API bootstrap smoke run. No model was fitted and no prediction was "
            "produced; this record establishes the runs ledger and proves the "
            "run-provenance path end to end."
        ),
        repo=REPO_ROOT,
    )
    print(f"[OK] run logged run_id={rec.run_id} git_commit={rec.git_commit} dirty={rec.git_dirty}")

    assert ledger.verify_chain() and runs_ledger.verify_chain()
    print("[OK] both hash chains verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
