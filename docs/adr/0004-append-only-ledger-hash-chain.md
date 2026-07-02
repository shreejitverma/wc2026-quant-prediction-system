# ADR-0004: Append-only, hash-chained ledger in JSONL

- Status: accepted
- Date: 2026-07-01

## Context

The prediction/order ledger is the evidentiary record for whether the system has real edge.
If a prediction can be quietly rewritten after the result is known, every backtest and every CLV number is worthless.
Two properties are required: append-only (never mutate) and tamper-evident (edits are detectable).

## Decision

We will store the ledger as newline-delimited JSON (JSONL), opened only in append mode and fsync'd on write.
Each entry carries `prev_hash` (the previous entry's `row_hash`) and its own `row_hash` = SHA-256 over the canonical JSON of `{seq, ts_utc, kind, prev_hash, payload}`.
`verify_chain()` recomputes the chain from genesis and returns False on any sequence gap, broken link, or edited payload.
See `wc2026.ledger`.

## Alternatives rejected

- **Parquet for the ledger** — Parquet files are immutable columnar blobs; appending one row means rewriting a file, which is the opposite of an audit log. Parquet is used for the *processed data* layer (ADR-0002), not the ledger.
- **A database table** — mutable by definition; "append-only" would be a convention enforced by discipline, not by structure.
- **No hash chain, just timestamps** — timestamps are trivially editable; the chain is what makes tampering detectable rather than merely discouraged.

## Consequences

The ledger is human-inspectable, OS-level append-only, and cryptographically tamper-evident.
DuckDB reads it directly for evaluation queries.
Cost: one small file that grows over time; compaction/rotation is a future optimization if the quote cadence makes it large (noted, not needed for v1).
Failure mode avoided: discovering, after losing money, that the "edge" was a rewritten backtest.
