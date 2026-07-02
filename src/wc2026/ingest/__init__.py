"""Phase 1: data and intelligence acquisition.

Every module here follows the fetch/parse separation:
  - fetch_*()  : thin I/O; writes raw payload to RawStore; idempotent (no-op if exists)
  - parse_*()  : pure function; takes raw bytes/str; returns validated Python objects
  - Tests are hermetic (no network); fixtures live in tests/ingest/fixtures/

The only write path for raw data is RawStore.write() which is append-once:
re-fetching the same source+name+date is a no-op, so pipelines are idempotent.
"""
