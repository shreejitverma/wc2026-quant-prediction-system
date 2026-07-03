# ADR-0004: Append-Only, Hash-Chained Ledger in JSONL

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Shreejit Verma

---

## Context

**The ledger is the evidentiary record for whether the system has real edge.**

Consider what happens without a tamper-evident ledger. An operator runs a live system for 3 months, loses $800, and tries to understand why. They go back and re-examine their backtest predictions. But without a tamper-proof audit trail, there is no way to know whether a historical backtest was *genuinely made before the fact* or *retroactively adjusted* after seeing the actual result.

This isn't a hypothetical concern — it is the dominant source of reported "alpha" in retail sports betting communities. The human brain is extremely good at convincing itself that it "knew" a result was likely, *after* seeing the result. Without a timestamp-locked, hash-chained record, no one (including yourself) can be fully confident.

**Two properties are required:**
1. **Append-only**: Once a row is written, it cannot be modified.
2. **Tamper-evident**: Any modification to any historical row is immediately detectable.

---

## Decision

### Storage Format

The ledger is stored as **newline-delimited JSON (JSONL)**, opened only in `append` mode and `fsync`'d on every write.

Why JSONL (not Parquet, not SQLite):
- **Append semantics**: Each line is an independent, complete JSON object. Appending one line is O(1) and does not require touching any other data.
- **Human-readable**: An operator can `tail -f data/ledger/ledger.jsonl` during a live session to monitor every quote and fill in real time, without any tooling.
- **Crash-safe**: A crash mid-write leaves the last line incomplete and truncatable; all prior lines are intact and valid.

### The Hash Chain

Every ledger entry contains:
- `seq`: A monotonically increasing sequence number.
- `ts_utc`: ISO 8601 UTC timestamp of the event.
- `kind`: Event type (`quote_submitted`, `quote_filled`, `quote_cancelled`, `prediction`, etc.).
- `payload`: The event-specific data (contract ID, fair value, price, size, model weights...).
- `prev_hash`: The SHA-256 hash of the **previous entry's canonical JSON**.
- `row_hash`: SHA-256 of `canonical_json({seq, ts_utc, kind, prev_hash, payload})`.

**The chain works as follows:**

```
Entry 1: { seq:1, ..., prev_hash: "genesis", row_hash: "a4b2c3..." }
Entry 2: { seq:2, ..., prev_hash: "a4b2c3...", row_hash: "f7e9a1..." }
Entry 3: { seq:3, ..., prev_hash: "f7e9a1...", row_hash: "d0e8b4..." }
```

If an attacker modifies Entry 1's payload (to erase a losing trade), Entry 1's `row_hash` changes. But Entry 2's `prev_hash` still contains the *old* `row_hash` of Entry 1. The chain is broken at Entry 2. `verify_chain()` detects this immediately.

### Verification

```python
from wc2026.ledger import verify_chain

result = verify_chain()
# Returns: { valid: True, entries_checked: 1243 }
# Or:      { valid: False, broken_at_seq: 847 }
```

`verify_chain()`:
1. Reads every line in `ledger.jsonl`.
2. Verifies the sequence numbers are contiguous (no gaps).
3. For each entry, recomputes `row_hash` from its canonical JSON and checks it matches the stored `row_hash`.
4. Checks that each entry's `prev_hash` matches the `row_hash` of the previous entry.
5. If any check fails, returns `False` with the sequence number of the first broken link.

This function runs in the CI pipeline (`phase0_selfcheck.py`) and at startup of the live execution engine.

---

## Worked Example: What Tampering Looks Like

Suppose entry seq=100 records a losing trade for -$200. An operator manually edits the JSONL file to change `profit_usd: -200` to `profit_usd: 50`:

1. Entry 100's `payload` is now different from what was originally hashed.
2. Entry 100's `row_hash` is now stale (was computed from the original payload).
3. Entry 101's `prev_hash` = the original `row_hash` of entry 100.
4. **Recomputing entry 100's hash from the modified payload produces a different value.**
5. `verify_chain()` detects the mismatch at seq=101: "prev_hash mismatch — chain broken at seq=101."

**The tamper is detected even if the operator also tries to update `row_hash`** — because then entry 101's `prev_hash` still doesn't match the new `row_hash` of entry 100, unless the operator recomputes *every subsequent entry* in the chain. Doing so leaves a timestamp trail in git history.

---

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| **Parquet for the ledger** | Parquet files are immutable columnar blobs. Appending one row means rewriting the entire file — the opposite of an audit log's requirements. |
| **A database table** | Mutable by definition. "Append-only" would be a convention enforced by discipline, not by structure. A `DELETE` or `UPDATE` statement would silently remove evidence. |
| **Timestamps only (no hash chain)** | Timestamps are trivially editable with `touch`. The chain is what makes tampering *detectable* rather than merely *discouraged*. |
| **A blockchain** | Massively over-engineered for a single-operator system. A JSONL hash chain provides the same guarantees with a 50-line Python implementation. |

---

## Consequences

### Positive
- The ledger is **human-inspectable, OS-level append-only, and cryptographically tamper-evident**.
- DuckDB reads the JSONL directly for evaluation queries: `SELECT * FROM read_json_auto('ledger.jsonl')`.
- Any claim of "X% return over Y matches" backed by the ledger is independently auditable.

### Negative / Cost
- A single file that grows indefinitely. Compaction/rotation is a future optimization if the quote cadence creates files >1GB (not needed for v1).
- The cryptographic chain adds ~1ms of hashing overhead per write — completely negligible.

### Failure Mode Avoided
Discovering, after losing money, that the claimed "edge" was a backtest that was retroactively adjusted to match actual results.
