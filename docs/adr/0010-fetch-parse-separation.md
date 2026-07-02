# ADR-0010: Fetch/parse separation in every ingest module

- Status: accepted
- Date: 2026-07-01

## Context

Ingest modules must be testable without network access (hermetic tests), reproducible (raw payloads available for re-parse), and debuggable (raw is always on disk before any transformation runs on it).

## Decision

Every ingest module exposes two distinct layers:
- `fetch_*()`: thin I/O; writes the raw payload to RawStore; idempotent (no-op if file exists); handles rate limiting and retry.
- `parse_*()`: pure function; takes raw `str`/`bytes`; returns validated Python objects; no I/O, no side effects.

All tests for parse logic use file fixtures, never the network. Fetch logic is tested by verifying RawStore idempotency and meta file creation, also without network (using a mock or pre-seeded store).

## Alternatives rejected

- **Parse inside fetch in one function** - cannot test parse logic without hitting the network; raw payload is not preserved.
- **Parse on-the-fly, discard raw** - breaks reproducibility (cannot re-parse with a fixed schema change without re-fetching).

## Consequences

- Raw payloads (as received) are always available for debugging and re-parse.
- Tests are fast, hermetic, and run in CI without network access.
- Schema changes trigger a re-parse pass on stored raws, not a re-fetch.
- Failure mode avoided: a parse bug that silently produces wrong training data without a recoverable raw to debug against.
