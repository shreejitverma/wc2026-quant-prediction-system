"""wc2026: World Cup 2026 prediction, pricing, and market-making system.

Phase 0 provides the honesty harness that every later phase depends on:
  - time_utils : UTC-only timestamp discipline
  - hashing    : content-addressable hashing + git provenance
  - pit        : the single point-in-time (leak-proof) access primitive
  - ledger     : append-only, hash-chained, tamper-evident ledger
  - runs       : reproducible experiment/run records
  - config     : strict (extra-forbidding) Pydantic config
"""

__version__ = "0.0.1"
