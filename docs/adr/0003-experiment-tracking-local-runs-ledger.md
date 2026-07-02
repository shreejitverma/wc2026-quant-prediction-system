# ADR-0003: Experiment tracking — local runs ledger, not MLflow/W&B

- Status: accepted
- Date: 2026-07-01

## Context

Every model fit and evaluation must be reproducible bit-for-bit and comparable over time.
The requirement is *provenance and reproducibility*, not dashboards.

## Decision

We will record runs as append-only entries in an `AppendOnlyLedger` (`wc2026.runs.log_run`).
Each `RunRecord` captures: run_id, created_at (UTC), git commit, git-dirty flag, and content hashes of config, data snapshot, and feature matrix, plus the metrics produced.
Because runs live in the hash-chained ledger, the experiment history is itself immutable and tamper-evident.

## Alternatives rejected

- **MLflow (local)** — a tracking server, backend DB, and artifact store to run and maintain; its UI is nice-to-have, but the property that matters (re-derivable, un-rewritable history) comes from hash-everything + append-only, which MLflow does not itself guarantee. Clean upgrade point: point an MLflow logger at the same RunRecords later if a UI is wanted.
- **Weights & Biases** — cloud dependency and data egress for a solo, privacy-sensitive trading project; rejected on principle and cost.
- **Ad hoc CSV of results** — no provenance, no tamper-evidence, no git/config linkage; this is how "great results" become un-reproducible.

## Consequences

Any historical metric can be traced to the exact code, config, and data that produced it.
No tracking infrastructure to operate.
Failure mode avoided: a promising backtest number that cannot be reproduced when it is time to trust it with capital.
