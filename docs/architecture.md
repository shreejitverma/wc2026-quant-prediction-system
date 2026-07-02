# System Architecture

One closed loop with an honesty harness bolted to the outside.
Strip away the phase numbering and everything below is either *the loop* (turning information into quotes) or *the harness* (making self-deception structurally hard).

## The loop (data -> belief -> price -> quote -> fill)

```
                 ┌─────────────────────────────────────────────────────────────┐
                 │                     HONESTY HARNESS                           │
                 │  append-only ledger · hash-everything · pre-registration ·   │
                 │  model tournament (proper scores + CLV as north star)        │
                 └─────────────────────────────────────────────────────────────┘
                                   ▲ instruments every stage ▼

  ingest (batch + event-driven)
      │   Tier1 results/Elo · Tier2 squad/player · Tier3 Kalshi/Poly books ·
      │   Tier4 venue/weather/ref · Tier5 LLM news (router, never a signal)
      ▼
  immutable raw store (dated, as-received)  ──►  clean / normalize  ──►
      ▼
  point-in-time feature store   [ get_features(match_id, as_of_ts) — the ONE gate ]
      ▼
  model layer  (M1 Dixon-Coles · M2 state-space · M3 Bayesian hierarchical ·
      │         M4 player-aggregation · M5 gradient boosting · M6 market-implied)
      ▼         every model -> full scoreline distribution, common interface
  meta-model / ensembler  (out-of-sample proper scores only; shrink to market)
      ▼
  tournament simulation engine  (exact 2026 rules; 100k–1M paths; persists the
      │                          FULL JOINT DRAW MATRIX — the crown jewel)
      ▼
  fair-value pricer  (fees · settlement timing/discount · resolution risk ·
      │               uncertainty band from the Phase 3 uncertainty layer)
      ▼
  contract mapper  [ HARD GATE: settlement text parsed & matched before pricing ]
      ▼
  quoting engine  (spread/size = f(uncertainty, edge, inventory, adverse selection))
      ▼
  execution:  PaperExchange (recorded books)  ──promotion gate──►  live clients
      ▼
  append-only prediction & order ledger  ──►  evaluation / model racing
```

## The harness (why the loop can be trusted)

Four instruments, all live from Phase 0:

1. **Append-only, hash-chained ledger** (`wc2026.ledger`) — every prediction, price, quote, order, fill is written once and never mutated; tampering breaks the chain and `verify_chain()` detects it.
2. **Hash-everything reproducibility** (`wc2026.hashing`, `wc2026.runs`) — every run records git commit + config/data/feature hashes, so any historical output is re-derivable bit-for-bit.
3. **Pre-registration** (`docs/preregistrations/`) — metric, threshold, and required sample size are frozen *before* each backtest or promotion gate. No moving goalposts.
4. **Point-in-time gate** (`wc2026.pit`) — the single leak-proof access path, enforced by property tests wired into pre-commit.

## Where the edge is — and is not

Edge = model quality + information *timing* (the lineup drop ~60–75 min pre-kickoff is the biggest scheduled information event) + settlement-rule precision + cross-market/joint **coherence** pricing.
Edge is **not** speed.
Retail-dominated, second-scale, binary-payoff books do not reward tick-shaving.
Speed pays in exactly three narrow places, all defensive: order-book **recording fidelity** (honest fill sim + CLV), **quote-pull kill switches** (don't be the stale quote a sharp picks off after a goal/red card), and **reconciliation** (book matches the exchange every cycle).
See `docs/adr/0006-edge-thesis-coherence-settlement-timing.md`.

## Stack

cron + DuckDB + Parquet + plain Python is the default.
Anything heavier (Kafka/Airflow/K8s) requires an ADR naming the measured bottleneck it removes.
A C++ hot path is proposed only after a profiler says so, never before.
See `docs/adr/0002-storage-stack-duckdb-parquet.md`.

## Phase map

| Phase | Name | Status |
|------|------|--------|
| 0 | Architecture, documentation, experiment discipline | **built (this delivery)** |
| 1 | Data & intelligence acquisition | next |
| 2 | Point-in-time feature store | pending |
| 3 | Model suite (M1–M6 + ensembler + uncertainty) | pending |
| 4 | Tournament simulation engine (joint distribution) | pending |
| 5 | Fair value, contract mapping, cross-venue pricing | pending |
| 6 | Market-making & execution engine (paper -> live) | pending |
| 7 | Evaluation, model racing, backtesting | pending |
| 8 | Live operations, in-play option, model decay | pending |
