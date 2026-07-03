# WC2026 Prediction System — Master Plan & Progress Log

**Last updated:** 2026-07-03 (All Phases 0–9 Complete & Verified)
**Repo:** `/Users/shreejitverma/github/footbal_prediction`
**Python:** 3.12 (uv-managed, `.python-version` pinned)
**Stack:** Python + DuckDB + Parquet + JSONL + plain cron (Vite/React Router SPA frontend)

---

## How to Resume in a New Session

```bash
cd /Users/shreejitverma/github/footbal_prediction
make verify                             # confirms the full baseline is green
./run.sh                                # launches the full API & UI stack
```

---

## Operator Profile

- **Background**: Senior quant developer, 7+ years: C++ AMM at BNP CIB, Versor Investments quant dev, BofA FICC, LogiNext senior SWE.
- **Academic & Professional Certifications**: MS Financial Engineering (Stevens), MS CS (Georgia Tech), MScFE (WorldQuant). CFA L1.
- **Stack Fluency**: Python (NumPy/Polars/PyTorch/XGBoost/CVXPY/statsmodels), C++ (FPGA/lock-free/DPDK), KDB+/Q, SQL/DuckDB, Spark/Kafka/Airflow, Docker/K8s.
- **Edge Focus**: Prediction-market edge is model quality, information timing, settlement precision, and coherence pricing — **not speed**. Engineering rigor is spent on: recording fidelity, quote-pull kill switches, and reconciliation.
- **Design Philosophy**: Default to cron + DuckDB + Parquet + plain Python. Avoid heavy infrastructure unless backed by a measured latency benchmark (see [ADR-0002](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0002-storage-stack-duckdb-parquet.md)).

---

## System Architecture Map

```
ingest (batch + event-driven)
  Tier 1: results/Elo · Tier 2: squad/player · Tier 3: Kalshi/Poly books
  Tier 4: venue/weather/ref · Tier 5: LLM news (router, never a signal)
         ↓
immutable raw store  →  clean/normalize
         ↓
point-in-time gate (as_of ts)  →  DuckDB Feature Store (Parquet-backed)
         ↓
modeling suite  (M1-M6)  →  meta-model ensembler (BFGS Log-Loss pool)
         ↓
tournament simulation  (100k paths; full joint draw matrix)
         ↓
fair-value pricer  &  contract mapper (settlement rules resolved)
         ↓
quoting engine  (Avellaneda-Stoikov reservations)
         ↓
PaperExchange  ──promotion gate──► live execution
         ↓
append-only ledger (JSONL, hash-chained)  →  walk-forward evaluation / CLV
         ↓
Vite React Operator Console (real-time WebSockets L2 streaming)
```

**Honesty harness (operational invariants):**
1. **[tamper-evident ledger](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0004-append-only-ledger-hash-chain.md)**: append-only JSONL with SHA-256 hash chains verified on startup.
2. **reproducible runs**: captures exact git commit + config hash + input hashes on every execution.
3. **pre-registration gates**: validation thresholds committed to git *before* running evaluation code.
4. **[point-in-time gate](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0005-point-in-time-gate.md)**: single data read-path enforced by Hypothesis property-based tests in pre-commit.

---

## Phase Status Summary

All phases of the quantitative engine and operator console are fully implemented, passing a rigorous test suite of 168 tests.

| Phase | Description | Status | Verification Command |
|---|---|---|---|
| **0** | Architecture, docs, experiment discipline | ✅ **COMPLETE** | `make verify` (harness checks pass) |
| **1** | Data & intelligence acquisition | ✅ **COMPLETE** | `uv run python scripts/phase1_fetch_smoke.py` |
| **2** | Point-in-time feature store | ✅ **COMPLETE** | `uv run python scripts/phase2_selfcheck.py` |
| **3** | Model suite (M1–M6 + Meta-Ensembler) | ✅ **COMPLETE** | `uv run pytest tests/unit/test_models.py` |
| **4** | Tournament simulation engine | ✅ **COMPLETE** | `uv run pytest tests/unit/test_simulator.py` |
| **5** | Fair value, contract mapping, coherence engine | ✅ **COMPLETE** | `uv run pytest tests/unit/test_pricing.py` |
| **6** | Market-making & execution engine | ✅ **COMPLETE** | `uv run pytest tests/unit/test_execution.py` |
| **7** | Evaluation, model racing, backtesting | ✅ **COMPLETE** | `uv run pytest tests/eval/` |
| **8** | Live operations, cron pipeline, kill-switches | ✅ **COMPLETE** | `uv run python -m wc2026.ops.cron backtest` |
| **9** | Frontend Operator Console | ✅ **COMPLETE** | `npm run test:e2e` (Playwright E2E pass) |

---

## Detailed Implementation Log

### Phase 0 — Architecture, Docs, and Experiment Discipline ✅ COMPLETE
- **Infrastructure built**: Created core modules for UTC-only timestamp discipline ([time_utils.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/time_utils.py)), git-reproducibility logging ([hashing.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/hashing.py)), append-only hash-chained auditing ([ledger.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ledger.py)), and strict configuration fencing ([config.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/config.py)).
- **PIT Gate**: Built [pit.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/pit.py) enforcing the leak-proof `as_of(ts)` gate, backed by property-based tests.
- **Verification**: `make verify` successfully compiles ruff checks, runs all unit/property tests, and executes the Phase 0 self-check smoke script.

### Phase 1 — Data & Intelligence Ingestion ✅ COMPLETE
- **Ingest modules**: Separation of fetch and parse logic ([fetch/parse separation](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0010-fetch-parse-separation.md)) built for:
  - martj42 international match results ([results.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ingest/results.py))
  - eloratings.net World Football Elo ratings ([elo.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ingest/elo.py))
  - Kalshi public API L2 orderbooks and markets ([kalshi.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ingest/kalshi.py))
  - Polymarket Gamma + CLOB API mappings ([polymarket.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ingest/polymarket.py))
- **Team Crosswalk**: Dynamic name normalizer ([crosswalk.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ingest/crosswalk.py)) mapping 240+ international team variations to a unified canonical set.
- **Verification**: hermetic fixture tests inside `tests/ingest/` run with zero network dependencies in CI.

### Phase 2 — Point-in-Time Feature Store ✅ COMPLETE
- **Storage engine**: Implemented [store.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/features/store.py) using an embedded DuckDB database writing to partitioned Parquet files.
- **Feature calculation**:
  - Reconstructs Elo histories sequentially with custom K-factor adjustments ([elo_hist.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/features/elo_hist.py)).
  - Calculates altitude profiles and team rest days ([match_ctx.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/features/match_ctx.py)).
  - De-vigs Kalshi/Polymarket markets using Proportional, Power, and Shin methods ([market_fv.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/features/market_fv.py)).
- **Verification**: `test_store_pit.py` runs 11 unit tests and a Hypothesis property test validating that future features are hidden.

### Phase 3 — Advanced Model Suite ✅ COMPLETE
The modeling suite ([src/wc2026/models/](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/)) provides six distinct predictive architectures sharing a unified interface:

1. **M1: Dixon-Coles Bivariate Poisson** ([dixon_coles.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/dixon_coles.py))
   - Implements Dixon & Coles (1997) goal-likelihood with $\rho$ low-score dependence correction and exponential time-decay ($w(t) = e^{-\xi \Delta t}$).
2. **M2: Dynamic State-Space Filter** ([state_space.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/state_space.py))
   - Sequential Elo-like rating filter updating attack/defense parameters via Poisson gradient descent.
3. **M3: Bayesian Hierarchical Goals** ([hierarchical.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/hierarchical.py))
   - JAX/numpyro MCMC model utilizing the No-U-Turn Sampler (NUTS) to pool team variances and enforce shrinkage.
4. **M4: Player-Aggregation** ([player_agg.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/player_agg.py))
   - Bottom-up expected goals (xG) aggregator that updates predictions dynamically as lineups drop.
5. **M5: Gradient Boosting (LightGBM)** ([gbm.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/gbm.py))
   - Decision-tree regressor optimizing a Poisson objective to capture non-linearities like altitude limits and rest days.
6. **M6: Market-Implied Bivariate Poisson** ([market_implied.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/market_implied.py))
   - Backwards-inverts live 1X2 market prices into a consistent 15×15 probability matrix using L-BFGS-B optimization.
7. **Meta-Model Ensembler** ([meta_ensemble.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/meta_ensemble.py))
   - Dynamically blends models using Log-Opinion Pooling (weighted geometric mean) or Linear Pooling, with weights optimized via out-of-sample Log-Loss minimization.

### Phase 4 — Tournament Simulation Engine ✅ COMPLETE
- **Simulation framework**: Implemented a highly vectorized simulator ([engine.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/simulator/engine.py)) running 100,000 Monte Carlo paths in milliseconds.
- **Tournament rules**:
  - Implements the complete FIFA group stage ruleset, including points, goal difference, and head-to-head tiebreakers ([group_stage.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/simulator/group_stage.py)).
  - Includes the best third-place teams progression lookup tables ([bracket_rules.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/simulator/bracket_rules.py)).
  - Simulates knockout extra time and shootouts ([knockout.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/simulator/knockout.py)).
- **Simulator Bridge**: Maps DuckDB features to the simulation inputs ([bridge.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/simulator/bridge.py)).

### Phase 5 — Fair Value, Contract Mapping, and Coherence Engine ✅ COMPLETE
- **Fair-Value Pricing**: Maps probabilities from the tournament simulator to specific contract payoffs minus exchange fee schedules ([fair_value.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/pricing/fair_value.py)).
- **Contract Mapper**: Matches arbitrary exchange contract descriptions (e.g. Kalshi " KXWCADVANCE ") to specific simulator events ([mapper.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/pricing/mapper.py)).
- **Coherence Engine**: Compares internal fair-value bounds against live Level 2 orderbook bids/asks to output ranked EV reports ([coherence.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/pricing/coherence.py)).

### Phase 6 — Market-Making & Execution Engine ✅ COMPLETE
- **Quoting Engine**: Adapts the Avellaneda-Stoikov inventory-control model to binary contracts, adjusting spreads and reservation prices as portfolio inventory shifts ([quoting.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/execution/quoting.py)).
- **Portfolio Optimization**: Solves fractional-Kelly allocations using CVXPY with Clarabel/SCS conic solvers to handle the covariance matrix constraints ([portfolio.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/execution/portfolio.py)).
- **Safety Guards**: Implemented real-time staleness detectors and daily P&L stop kill-switches ([kill_switches.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/execution/kill_switches.py)).

### Phase 7 — Evaluation, Model Racing, and Backtesting ✅ COMPLETE
- **Metrics**: Computes proper scoring rules: Categorical Log Loss, Brier Score, and Ranked Probability Score (RPS) ([metrics.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/eval/metrics.py)).
- **Backtest Engine**: Runs walk-forward cross-validation backtests over historical tournament windows to optimize ensembler weights ([backtest.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/eval/backtest.py)).

### Phase 8 — Live Operations Pipeline ✅ COMPLETE
- **Orchestration**: The master loop ([cron.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ops/cron.py)) links features, models, simulator, pricing, and execution. Supported modes: `backtest`, `live` (paper/live execution), and `coherence` (cross-venue arbitrage).

### Phase 9 — Frontend Operator Console ✅ COMPLETE
- **Framework & Layout**: Built a desktop-first Vite React SPA utilizing Tailwind CSS for high density layout.
- **State Managers**: Zustand handles the active trading blotter (`tradingStore.ts`) and risk limits; TanStack Query manages endpoint polling and cache invalidation.
- **L2 Orderbooks**: Displays real-time bids/asks streaming from a backend multiplexed WebSocket connection (`ws.py`).
- **E2E Testing**: Playwright E2E suite (`npm run test:e2e`) runs in a sandbox, validating banners, opportunities, and the kill-switch flow.

---

## Master Configurations (configs/default.yaml)

```yaml
mode: paper                     # default mode: paper (live requires promotion)
risk:
  bankroll_usd: 5000.0          # total trading capital
  kelly_fraction: 0.25          # conservative quarter-Kelly fraction
  max_position_per_event_usd: 100.0
  max_portfolio_drawdown_pct: 0.20
  min_edge: 0.03                # minimum edge (3c) required to execute
kill_switch:
  enabled: true
  max_data_staleness_seconds: 120
  pnl_stop_usd: 250.0           # stop trading if daily loss exceeds this
  reconcile_every_cycle: true
venues:
  kalshi_enabled: true
  polymarket_enabled: true
  betfair_enabled: false        # US geo-restricted; sharp odds de-vigged from Pinnacle
```

---

## Active Open Items

1. **Exchange API Authentication**: Complete Polymarket Gamma credentials configuration inside the private secrets files when live mode promotion triggers.
2. **CLV Tracking Extension**: Update the evaluation module (`src/wc2026/eval/`) to continuously pull Kalshi post-match trades to calculate realized CLV.
3. **M3 Warmup Tuning**: Adjust `BayesianHierarchicalModel` chains or compile M3 to JAX primitives if CPU sampling times during the live tournament exceed the 60-second execution window.
