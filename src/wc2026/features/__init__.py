"""Phase 2: Point-in-time feature store.

The single sanctioned access path for any downstream consumer (model, backtest,
live pricer) is:

    from wc2026.features.store import FeatureStore
    store = FeatureStore("data/processed/features.duckdb")
    row = store.get_features(match_id="MEX-ENG-20260705", as_of_ts=ts)

No feature returned by `get_features` can have a `knowable_at` > `as_of_ts`.
This invariant is enforced by DuckDB's WHERE clause in the store, and proven by
property-based tests in tests/features/test_store_pit.py that are wired into
pre-commit alongside the Phase 0 primitive tests.

Feature families in this phase:
  elo_hist   : historical Elo reconstructed from results timeline (not current)
  match_ctx  : neutral, stage, rest days, altitude, dead-rubber flag
  market_fv  : de-vigged Kalshi mid-prices (with admissibility guard)
"""
