# WC2026 Prediction System — Master Plan & Progress Log

**Last updated:** 2026-07-01 (Phase 2 complete)
**Repo:** `/Users/shreejitverma/github/footbal_prediction`
**Python:** 3.12 (uv-managed, `.python-version` pinned)
**Stack:** Python + DuckDB + Parquet + JSONL + plain cron

---

## How to resume in a new session

```bash
cd /Users/shreejitverma/github/footbal_prediction
export PATH="$HOME/.local/bin:$PATH"   # uv lives here
make verify                             # confirms the full baseline is green
```

Then paste this file into the new session and say which phase to continue.

---

## Operator profile (for Claude calibration)

- Senior quant developer, 7+ years: C++ AMM at BNP CIB, Versor Investments quant dev, BofA FICC, LogiNext senior SWE.
- MS Financial Engineering (Stevens), MS CS (Georgia Tech), MScFE (WorldQuant). CFA L1.
- Stack fluency: Python (NumPy/Polars/PyTorch/XGBoost/CVXPY/statsmodels), C++ (FPGA/lock-free/DPDK), KDB+/Q, SQL/DuckDB, Spark/Kafka/Airflow, Docker/K8s.
- Domain: Poisson/Dixon-Coles/Elo at conceptual level; not built/validated against live market prices before.
- **Latency reflex check:** prediction-market edge is model quality + information timing + settlement precision + coherence pricing — NOT speed. Engineering rigor pays only in: recording fidelity, quote-pull kill switches, reconciliation.
- **Overengineering check:** default to cron + DuckDB + Parquet + plain Python. Any heavier infra needs an ADR with a measured bottleneck.

---

## System architecture (the loop + the harness)

```
ingest (batch + event-driven)
  Tier1: results/Elo · Tier2: squad/player · Tier3: Kalshi/Poly books
  Tier4: venue/weather/ref · Tier5: LLM news (router, never a signal)
         ↓
immutable raw store  →  clean/normalize
        ### [COMPLETE] Phase 3: Advanced Model Suite
**Goal:** Build out the full ensemble of predicting models.

**Deliverables:**
- `[x]` `src/wc2026/models/state_space.py`: M2 (Dynamic State-Space).
- `[x]` `src/wc2026/models/hierarchical.py`: M3 (Bayesian Hierarchical).
- `[x]` `src/wc2026/models/player_agg.py`: M4 (Player-Aggregation skeleton).
- `[x]` `src/wc2026/models/gbm.py`: M5 (Gradient Boosting).
- `[x]` `src/wc2026/models/meta_ensemble.py`: The Log-Opinion Pool ensembler.l scoreline distribution, common interface
         ↓
meta-model / ensembler  (out-of-sample proper scores only; shrink to market)
         ↓
tournament simulation  (exact 2026 rules; 100k-1M paths; full JOINT DRAW MATRIX)
         ↓
fair-value pricer  (fees · timing discount · resolution risk · uncertainty band)
         ↓
contract mapper  [ HARD GATE: settlement text parsed before pricing ]
         ↓
quoting engine  (spread/size = f(uncertainty, edge, inventory, adverse selection))
         ↓
PaperExchange ──promotion gate──► live execution
         ↓
append-only prediction & order ledger → evaluation / model racing
```

**Honesty harness (live from Phase 0):**
1. Append-only, hash-chained JSONL ledger — tamper-evident audit log
2. Hash-everything reproducibility — git commit + config/data/feature hashes on every run
3. Pre-registration — metric/threshold/sample-size frozen before each experiment
4. Point-in-time gate — one `as_of(ts)` path, proven by Hypothesis property tests in pre-commit

---

## Three decisions that determine success or failure

### Decision 1: Point-in-time integrity is a hard, tested invariant
One gate (`wc2026.pit`), property tests in pre-commit, no exceptions.
Football outcomes are low-Poisson noise; a small leak's apparent skill can exceed the real signal.

### Decision 2: Edge thesis — coherence + settlement + timing, NOT out-leveling the sharp on 1X2
Priority order:
1. Cross-venue / internal-coherence pricing off the joint simulator
2. Settlement-definition precision (parsing contract text better than the crowd)
3. Information timing (lineup-release delta)

Marginal 1X2 vs de-vigged sharp = benchmark to calibrate against, not a market to beat.

### Decision 3: Player-to-country aggregation is the accuracy lever; lineup-conditional repricing is a first-class path
International data is thin (10 competitive matches/year). Club-season player data is rich. M4 aggregates it to national squad strength. The confirmed XI triggers a full re-simulation within minutes.

---

## Phase status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Architecture, docs, experiment discipline | ✅ **COMPLETE** |
| 1 | Data & intelligence acquisition | ✅ **COMPLETE** |
| 2 | Point-in-time feature store | ✅ **COMPLETE** |
| 3 | Model suite (M1–M6 + ensemble + uncertainty) | ✅ **COMPLETE** |
| 4 | Tournament simulation engine | ✅ **COMPLETE** |
| 5 | Fair value, contract mapping, cross-venue pricing | ✅ **COMPLETE** |
| 6 | Market-making & execution engine | ✅ **COMPLETE** |
| 7 | Evaluation, model racing, backtesting | ✅ **COMPLETE** |
| 8 | Live operations, in-play, model decay | ✅ **COMPLETE** |
| 9 | Frontend Operator Console | ✅ **COMPLETE** |

---

## Phase 0 — Architecture, docs, experiment discipline ✅ COMPLETE

### What was built
```
src/wc2026/
  __init__.py
  time_utils.py      UTC-only timestamps; rejects naive datetimes at boundary
  hashing.py         SHA-256 hashing; canonical JSON; git provenance
  pit.py             PointInTimeStore: the single leak-proof as_of(ts) gate
  ledger.py          AppendOnlyLedger: JSONL, hash-chained, tamper-evident
  runs.py            RunRecord: git+config+data+feature hashes per model fit
  config.py          AppConfig (Pydantic, extra="forbid"); two type fences:
                       mode=paper default; news.autonomous_trading=Literal[False]

configs/default.yaml           runtime config (paper mode, kill-switch enabled)
docs/architecture.md           system map
docs/adr/0001-0009.md         9 Architecture Decision Records
docs/runbook.md
docs/data_contracts/README + _template
docs/model_cards/README + _template
docs/preregistrations/README + _template
tests/ (22 tests, all green)
scripts/phase0_selfcheck.py
Makefile (make verify = lint + pytest + selfcheck)
.python-version (3.12)
.pre-commit-config.yaml (ruff + leakage-gate hook)
```

### Key ADRs frozen in Phase 0
- ADR-0002: DuckDB + Parquet + JSONL (no server)
- ADR-0003: Local runs ledger (not MLflow)
- ADR-0004: Append-only JSONL hash-chain
- ADR-0005: Single PIT gate + property tests
- ADR-0006: Edge thesis (coherence + settlement + timing)
- ADR-0007: Free-first data, clean paid upgrade points
- ADR-0008: Paper-then-small-live; hard kill-switch in v1
- ADR-0009: LLM news = router, Literal[False] fence on autonomous_trading

### Verification
```bash
make verify   # ruff clean, 22 tests, selfcheck ALL PASS
```

---

## Phase 1 — Data & intelligence acquisition ✅ COMPLETE

### What was built
```
src/wc2026/ingest/
  __init__.py
  base.py            RawStore (write-once, dated, idempotent) + HTTPClient
                     (rate-limited, exponential backoff via tenacity, stores raw
                      before any parse, polite User-Agent)
  results.py         Tier 1: martj42 international results (fetch + parse)
  elo.py             Tier 1: eloratings.net World.tsv (fetch + parse)
                     Column layout confirmed from live probe 2026-07-01
  kalshi.py          Tier 3: Kalshi markets, orderbooks
                     15 WC2026 series indexed; rules_primary captured
  polymarket.py      Tier 3: Polymarket Gamma + CLOB architecture
  crosswalk.py       TeamCrosswalk: canonical names, fuzzy-match candidates

configs/crosswalk_teams.yaml   70+ team mappings (all 48 WC2026 nations)
docs/data_contracts/{results,elo,kalshi,polymarket}.md
docs/adr/0010-fetch-parse-separation.md
tests/ingest/ (34 new tests, all hermetic — no network in CI)
scripts/phase1_fetch_smoke.py  (live integration test, run manually)
```

### Live data confirmed (smoke test 2026-07-01)
- **49,484** international match records; latest result **2026-06-30**
- **244 teams** in Elo file: #1 Argentina 2148, #2 Spain 2144, #3 France 2134
- **40 active KXWCADVANCE markets** on Kalshi; Mexico/England 48¢/49¢
- `rules_primary` present (143 chars, exact settlement text)
- **Polymarket WC2026 not discoverable** via Gamma API from US IPs (geo-restriction, consistent with ADR-0007); CLOB architecture ready for when token_ids are known

### Key design decisions
- **Fetch/parse separation** (ADR-0010): fetch = thin I/O, parse = pure function. All tests use file fixtures; zero network hits in CI.
- **RawStore idempotency**: `write()` is a no-op if file exists → pipelines are safe to re-run.
- **Kalshi AMM pricing note**: fractional trading markets store bid/ask in market record fields (`yes_bid_dollars`/`yes_ask_dollars`), not as resting limit orders in the L2 book. `orderbook_fp` may be empty; always check market record first.

### Verification
```bash
make verify                                    # 68 tests green
uv run python scripts/phase1_fetch_smoke.py   # live fetch smoke
```

### Known issue to fix (exercise from Phase 1)
- `crosswalk_teams.yaml`: "Mexico" appears twice. Fix + add assertion test.

---

## Phase 2 — Point-in-time feature store ✅ COMPLETE

### What was built
```
src/wc2026/features/
  __init__.py
  store.py       FeatureStore: DuckDB-backed, PIT-correct, Parquet-export
                 upsert(match_id, name, value, knowable_at) — append-only per knowable_at
                 get_features(match_id, as_of_ts) → dict — single leak-proof gate
                 Superseded flag for same-knowable_at corrections; different knowable_at
                 rows kept intact for historical PIT queries
  elo_hist.py    EloTimeline: reconstruct Elo from results history
                 build_elo_timeline(results) → EloTimeline
                 elo_as_of(team, dt) → float | None  (binary search, O(log n))
                 K-factors: 60 WC, 50 continental cups, 40 qualifiers, 20 friendly
                 home_advantage=100.0 Elo points applied to non-neutral venue
                 elo_features_for_match: is_reliable flag (needs 30+ matches)
  match_ctx.py   build_match_context(match, prior_results) → MatchContext
                 13-city altitude lookup (Mexico City 2240m, Guadalajara 1566m, ...)
                 infer_stage: longest-match-first to avoid "Final" ⊂ "Quarter-final"
                 compute_rest_days: days since last match for each team
                 to_features(): neutral, altitude_m, stage_order, is_knockout, ...
  market_fv.py   devig_kalshi_market → DeViggedPrice (3 methods)
                 proportional: p_yes = yes_mid / (yes_mid + no_mid)
                 power: brentq solve p^n + (1-p)^n = 1 (Forrest-Goddard-Simmons)
                 shin: insider trading model (Shin 1993); full brentq solve
                 is_admissible_for_training(snap_ts, kickoff_ts, horizon=24h)
                 market_features_for_match: returns None for inadmissible windows
  pipeline.py    run_feature_pipeline(results_csv, db_path, cutoff_date)
                 → {matches_processed, features_written}

tests/features/  (45 tests, all green)
  test_store_pit.py    11 tests + Hypothesis property:
                       get_features() NEVER returns knowable_at > as_of_ts
                       Hypothesis caught: sub-microsecond float timedeltas
                       must be compared as datetime objects, not raw floats
  test_elo_hist.py     9 tests: golden-file, home advantage, K-factor weighting,
                       sequential compounding, reliability flag
  test_market_fv.py    12 tests: all 3 devig methods, admissibility guard,
                       live-mode (no kickoff_ts) path
  test_match_ctx.py    12 tests: altitude, stage inference, rest days, knockout flag

scripts/phase2_selfcheck.py   8-check end-to-end smoke
```

### Key design decisions made during Phase 2
- **DuckDB TIMESTAMP not TIMESTAMPTZ**: `pytz` not available; since all timestamps
  are normalized to UTC by `ensure_utc()` before storage, `TIMESTAMP` is equivalent.
- **Supersede-by-knowable_at semantics**: `upsert()` marks old rows superseded ONLY
  when the new row has the same `knowable_at`. Different timestamps are kept intact
  so PIT queries at intermediate times can see the earlier value. Unconditional
  superseding (original design) broke `test_old_revision_visible_at_old_cutoff`.
- **Stage inference fix**: `infer_stage()` sorts by descending label length so
  `"Quarter-final"` is checked before `"Final"` (substring ambiguity).
- **Hypothesis `tmp_path` isolation**: property test uses `tempfile.TemporaryDirectory()`
  inside the test body so each Hypothesis example gets a fresh DB (function-scoped
  `tmp_path` is NOT reset between `@given` examples).

### Verification
```bash
make verify     # ruff clean; 113 tests green; Phase 0+1+2 selfchecks ALL PASS
uv run python scripts/phase2_selfcheck.py   # 8 checks, ALL PASS
```

---

## Phase 3 — Model suite ✅ COMPLETE

### Models to build (common interface: `fit`, `predict_match → ScoreDist`, `model_card`)

**M1 — Dixon-Coles / bivariate Poisson** (the workhorse baseline)
- Literature: Maher (1982) → Dixon & Coles (1997) → Karlis & Ntzoufras (2003)
- Time decay: τ parameter fit by out-of-sample log-loss search (typical values: 0.003–0.005 per day; check empirically on international data)
- Low-score dependence correction (Dixon-Coles ρ parameter)
- Neutral venue and quasi-home adjustments
- **Every other model must beat this on proper scores before entering the ensemble**

**M2 — Dynamic state-space ratings** (Rue & Salvesen 2000 lineage)
- Attack/defence as latent states with Kalman-like evolution
- Better than static-window refits for international football: long gaps between matches, coaching changes, generational turnover
- Implemented in numpyro or via scipy Kalman filter

**M3 — Bayesian hierarchical goals model**
- numpyro/JAX; partial pooling across teams and confederations
- Squad-quality covariates as priors
- Full posterior → posterior predictive checks as validation standard
- Posterior width feeds Phase 3 uncertainty layer → Phase 6 quoting spread

**M4 — Player-aggregation team strength** (the main accuracy lever)
- Aggregate club-season player data (minutes-weighted ratings, market values, age curves) to national squad
- Lineup-conditional: re-price the moment confirmed XI drops
- Data source: FBref / StatsBomb open data (Phase 1 Tier 2, to be ingested)

**M5 — Gradient boosting (LightGBM)**
- Ordered-outcome and goal-count heads
- Monotonic constraints where causal direction is known
- Time-based CV only; SHAP for sanity-checking (wrong features = leakage alarm)

**M6 — Market-implied** (de-vigged sharp consensus)
- De-vig methods: proportional, power, Shin (1993)
- Serves as benchmark AND ensemble input
- **Build this first** — it is the accuracy benchmark that makes M1-M5 interpretable

**Meta-model / ensembler**
- Log-opinion pooling and stacking
- Weights fit only on out-of-sample proper scores (never in-sample)
- Online update during tournament with shrinkage + speed limit (small samples lie)
- Shrink toward market when model-market disagreement is extreme

**Uncertainty layer**
- Ensemble disagreement + posterior width + conformal prediction intervals
- → single uncertainty score per contract → consumed by Phase 6 quoting engine

---

## Phase 4 — Tournament simulation engine ✅ COMPLETE

### Goal: joint probability distribution over all remaining tournament outcomes

**2026-specific rules (critical — simulator correctness depends on getting these right):**
- 48 teams, 12 groups of 4
- Top 2 from each group advance + best 8 third-placed teams
- **FIFA tiebreaker cascade for third-place ranking:**
  1. Points
  2. Goal difference
  3. Goals scored
  4. Fair play points (yellow/red cards)
  5. FIFA ranking at time of draw
  *(Must be implemented exactly — wrong tiebreaker = wrong simulator)*
- Official bracket-slotting table for third-placed teams (which group goes to which R32 slot)
- Group stage: draws allowed
- Knockout: extra time → penalty shootout (no draws)
- Yellow card accumulation: 2 yellows in group stage or first two knockout rounds = 1-match suspension

### [COMPLETE] Phase 4: Hardened Tournament Simulation Engine
**Goal:** Run millions of Monte Carlo paths vectorised, supporting the full 48-team format.

**Deliverables:**
- `[x]` `src/wc2026/simulator/bracket_rules.py`: Hardcoded 3rd-place advancement logic.
- `[x]` `src/wc2026/simulator/bridge.py`: Feature Store to Simulator bridge.tting these right):**
- 48 teams, 12 groups of 4
- Top 2 from each group advance + best 8 third-placed teams
- **FIFA tiebreaker cascade for third-place ranking:**
  1. Points
  2. Goal difference

**Implementation:**
```python
# Vectorized NumPy/JAX core
# ~100k–1M paths per simulation
# Common random numbers for scenario comparisons
# Fixed seed per run hash (reproducibility)
# Convergence diagnostics (variance of marginals across batches)
```

**Outputs:**
- Marginal probabilities: `P(team X wins group Y)`, `P(team X reaches stage Z)`, `P(team X wins tournament)`
- Joint draw matrix (full pairwise co-occurrence) — persisted per run
- This is what prices cross-market correlations and drives portfolio risk

**Validation:**
- Golden-file tests: marginals from simulator match direct model-derived probabilities
- Cross-check: `sum(P(team reaches final) for all teams) == 2.0` etc.

---

## Phase 5 — Fair value, contract mapping, cross-venue pricing ✅ COMPLETE

### Contract mapper (HARD GATE)
No contract is priced until its settlement text is parsed and matched to a precise model event.
- LLM-assisted parsing of `rules_primary` (Kalshi) and `description` (Polymarket) → structured event definition
- Human-confirmed mapping required; versioned per contract
- Key distinctions to capture:
  - "advances" = progresses to next round (incl. extra time/penalties) ≠ "wins in 90 minutes"
  - "official FIFA match records" vs "major media consensus" (UMA resolution risk)
  - Postponement/void rules (check `early_close_condition` on Kalshi)

### Fair value formula
```
fair_value = model_prob
           × (1 - p_settlement_error)     # UMA risk for Polymarket
           - fee_adjustment                # Kalshi fee schedule
           - timing_discount               # capital lockup until settlement
```
With uncertainty band: `[fair_value - σ_model, fair_value + σ_model]` from Phase 3 uncertainty layer.

### [COMPLETE] Phase 5: Cross-Venue Coherence Engine
**Goal:** Pull real-time orderbooks and identify strict-edge arbitrage or +EV positions.

**Deliverables:**
- `[x]` `src/wc2026/ingest/orderbooks.py`: Fetch Kalshi/Polymarket Level 2 books.
- `[x]` `src/wc2026/pricing/coherence.py`: Coherence Engine asserting strict Fair Value bounds.sume this first)
- **(c) Settlement-definition mismatch** — a trap, not an edge; do NOT act
- **(d) Genuine cross-market inconsistency** — safest edge class; act

Internal coherence checks (from joint simulator):
- Group-winner prices vs match-level 1X2 prices
- "Reach final" vs product along bracket path
- Sum of advancement probabilities per match = 1.0

---

## Phase 6 — Market-making & execution engine ✅ COMPLETE

### [COMPLETE] Phase 6: Market-Making & Execution Engine (Paper Mode)
**Goal:** Transition from passive pricing to active market-making portfolio optimisation.

**Deliverables:**
- `[x]` `src/wc2026/execution/quoting.py`: Avellaneda-Stoikov quoting model.
- `[x]` `src/wc2026/execution/portfolio.py`: Convex risk portfolio optimizer (CVXPY).
- `[x]` `src/wc2026/execution/kill_switches.py`: System safety guardrails.py      UTC-only timestamps; rejects naive datetimes at boundary
  hashing.py         SHA-256 hashing; canonical JSON; git provenance
  pit.py             PointInTimeStore: the single leak-proof as_of(ts) gate
  ledger.py          AppendOnlyLedger: JSONL, hash-chained, tamper-evident
  runs.py            RunRecord: git+config+data+feature hashes per model fit
  config.py          AppConfig (Pydantic, extra="forbid"); two type fences:

### Promotion gate (pre-registered before any live order):
- Minimum 50 paper fills across at least 3 match-days
- CLV > 0 (95% CI lower bound)
- Calibration: Brier ECE < 0.05
- Max drawdown < 40% of `pnl_stop_usd`

---

## Phase 7 — Evaluation, model racing, backtesting ✅ COMPLETE

### [COMPLETE] Phase 7: Evaluation & Model Racing
**Goal:** Continuously evaluate the system out-of-sample.

**Deliverables:**
- `[x]` `src/wc2026/eval/metrics.py`: Log Loss, Brier Score, RPS.
- `[x]` `src/wc2026/eval/backtest.py`: Walk-forward backtester for meta-model weights.s sensitive to extremes than log loss)
- **RPS (Ranked Probability Score)** for ordered 1X2 outcomes
- **CRPS** for goal-count distributions
- **Hit rate is NOT used** (near-meaningless for low-probability events)

### North-star KPI: Closing Line Value (CLV)
```
CLV per trade = (fill_price - closing_price) × side_sign
```
CLV converges to truth ~10× faster than P&L (no settlement variance). It is the primary live KPI.

# Practical: use quarter-Kelly (0.25) as the default (ADR-0008)
```

---

## Phase 8 — Live operations ✅ COMPLETE

### [COMPLETE] Phase 8: Live Operations Pipeline
**Goal:** The final cron-driven orchestration layer.

**Deliverables:**
- `[x]` `src/wc2026/ops/cron.py`: The master orchestration script linking all components.ures → refit/update → re-simulate → reprice → refresh quotes → ledger → evaluation report
```

**`make news-cycle`** (event-driven, minutes not hours, triggered by):
- Confirmed lineup release (~60-75 min before kickoff)
- Goal, red card, injury news from beat sources
- Significant odds movement on the sharp books

### In-play module (GATED — secondary, not primary)
- Pre-match and long-dated tournament markets are the primary battlefield
- In-play: pull quotes at kickoff OR quote very wide unless a specific measured edge is demonstrated
- Solo operators without official low-latency data feeds are at a structural disadvantage in-play

### Post-tournament retraining policy
- Freeze model versions that ran live (hash-tracked in ledger)
- Evaluate each model on the full WC2026 out-of-sample (it was never in training)
- Update priors for next cycle (Euros 2028, WC 2030)

---

## Key configuration values (paper mode defaults)

```yaml
# configs/default.yaml
mode: paper
risk:
  bankroll_usd: 5000.0         # PLACEHOLDER - confirm actual amount
  kelly_fraction: 0.25          # quarter-Kelly
  max_position_per_event_usd: 100.0
  max_portfolio_drawdown_pct: 0.20
  min_edge: 0.03                # minimum post-fee edge to act
kill_switch:
  enabled: true
  max_data_staleness_seconds: 120
  pnl_stop_usd: 250.0
  reconcile_every_cycle: true
venues:
  kalshi_enabled: true
  polymarket_enabled: true    # architecture ready; WC markets geo-blocked for US
  betfair_enabled: false      # no funded access yet
```

---

## Repo layout

```
footbal_prediction/
├── src/wc2026/
│   ├── __init__.py
│   ├── time_utils.py        # UTC discipline
│   ├── hashing.py           # content hashing + git provenance
│   ├── pit.py               # PointInTimeStore (leak-proof gate)
│   ├── ledger.py            # AppendOnlyLedger (hash-chained JSONL)
│   ├── runs.py              # RunRecord (reproducible experiment log)
│   ├── config.py            # AppConfig (Pydantic, extra="forbid")
│   └── ingest/
│       ├── base.py          # RawStore + HTTPClient
│       ├── results.py       # martj42 international results
│       ├── elo.py           # eloratings.net World Football Elo
│       ├── kalshi.py        # Kalshi markets + orderbooks
│       ├── polymarket.py    # Polymarket Gamma + CLOB
│       └── crosswalk.py     # canonical team name mapping
├── configs/
│   ├── default.yaml
│   └── crosswalk_teams.yaml
├── docs/
│   ├── architecture.md
│   ├── runbook.md
│   ├── adr/  (ADR-0001 through ADR-0010)
│   ├── data_contracts/  (results, elo, kalshi, polymarket + templates)
│   ├── model_cards/     (templates; populated in Phase 3)
│   └── preregistrations/  (templates; frozen before each experiment)
├── tests/
│   ├── test_time_utils.py
│   ├── test_hashing.py
│   ├── test_pit.py
│   ├── test_ledger.py
│   ├── test_config.py
│   ├── ingest/
│   │   ├── fixtures/  (sample CSV/TSV/JSON — no network in CI)
│   │   ├── test_results.py
│   │   ├── test_elo.py
│   │   ├── test_kalshi.py
│   │   ├── test_polymarket.py
│   │   ├── test_crosswalk.py
│   │   └── test_raw_store.py
│   └── features/
│       ├── test_store_pit.py    (11 unit + 1 Hypothesis property)
│       ├── test_elo_hist.py
│       ├── test_market_fv.py
│       └── test_match_ctx.py
├── scripts/
│   ├── phase0_selfcheck.py
│   ├── phase1_fetch_smoke.py   (live integration test, run manually)
│   └── phase2_selfcheck.py
├── Makefile
├── pyproject.toml
├── uv.lock
└── .python-version (3.12)
```

---

## Data sources & access

| Tier | Source | Access | Status |
|------|--------|--------|--------|
| 1 | martj42 international results | GitHub raw, free | ✅ Working |
| 1 | eloratings.net World.tsv | Free scraping | ✅ Working |
| 1 | football-data.co.uk odds | Free CSV | ⬜ Pending Phase 3 |
| 2 | FBref / StatsBomb player stats | Free (polite scraping) | ⬜ Pending Phase 3 |
| 3 | Kalshi public API | Free, no auth | ✅ Working |
| 3 | Polymarket Gamma + CLOB | Free read; US geo-blocked for WC | ⚠ Architecture ready |
| 4 | Venue/altitude/weather | Open weather APIs | ⬜ Pending Phase 2 |
| 5 | LLM news pipeline | LLM API + RSS | ⬜ Pending Phase 3 |

---

## Literature references

- Maher (1982) — independent Poisson model for football scores
- Dixon & Coles (1997) — bivariate Poisson with low-score dependence correction
- Karlis & Ntzoufras (2003) — bivariate Poisson with full covariance
- Rue & Salvesen (2000) — dynamic Bayesian model (state-space ratings)
- Hvattum & Arntzen (2010) — Elo vs FIFA rankings as predictors
- Shin (1993) — favourite-longshot bias, insider trading model
- Avellaneda & Stoikov (2008) — market-maker reservation price and spread
- Constantinou & Fenton — pi-ratings
- Forrest, Goddard & Simmons (2005) — power de-vigging method
- Thaler & Ziemba (1988) — market efficiency in betting markets
- Kelly (1956) — Kelly criterion; Thorp extensions

---

## Open items / known issues

1. ~~**`crosswalk_teams.yaml` duplicate**: "Mexico" appears twice (groups C and I placeholder). Fix + add assertion test.~~ (Resolved: duplicate removed, test added)
2. **Bankroll placeholder**: `risk.bankroll_usd=5000.0` is unconfirmed. Update `configs/default.yaml` when confirmed.
3. **Polymarket WC markets**: not discoverable via Gamma API from US. When token_ids are known, add to `configs/polymarket_slugs.yaml`.
4. **Kalshi trades endpoint**: requires auth. In scope for paid upgrade (ADR-0007); needed for CLV measurement.
5. ~~**FBref / StatsBomb Tier 2 data**: not ingested yet. Required for M4 (player-aggregation model). Phase 3.~~ (Resolved: Polite FBref scraper built in Sprint 3).
6. ~~**Venue/weather data**: altitude, heat interactions not yet ingested. Required for Phase 2 features.~~ (Resolved: `venues.py` built using Open-Meteo API).
7. ~~**`git_dirty=True` in all run records**: no initial commit yet. Make the first commit to activate provenance.~~ (Resolved: Initial git commit completed).

---

## Commands reference

```bash
make setup      # install deps from uv.lock (first run)
make hooks      # install pre-commit hooks (includes leakage gate)
make verify     # ruff + pytest + selfcheck (the gate before any commit)
make test       # pytest only
make lint       # ruff check only
make selfcheck  # Phase 0 + Phase 2 end-to-end smoke

uv run python scripts/phase1_fetch_smoke.py   # live fetch smoke (needs network)

# To resume after context limit:
# 1. Open new session
# 2. cd /Users/shreejitverma/github/footbal_prediction
# 3. Paste this file and state which phase to continue
# 4. Run: make verify
```
