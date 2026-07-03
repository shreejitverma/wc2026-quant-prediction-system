# Walkthrough: End-to-End Prediction & Pricing Trace

This document provides a trace showing how the system calculates, prices, and records a single contract: **`Mexico beats USA FT`** (Home Win contract, Kalshi ticker `KX-WC26-MEXUSA-WIN`).

---

## The Lifecycle of a Prediction

```
[ Ingest: World.tsv ]
         │
         ▼
[ DuckDB Feature Store ] ───► PIT Filter (knowable_at <= as_of)
         │
         ▼
[ Model Suite (M1-M6) ] ───► Dixon-Coles Poisson Goals
         │
         ▼
[ Meta-Model Ensembler ] ───► Blended Win/Draw/Loss Probabilities
         │
         ▼
[ Quoting & De-vigging ] ───► Avellaneda-Stoikov Spreads
         │
         ▼
[ Ledger Logging ] ───► SHA-256 Hashed JSONL Blotter Row
```

---

## Phase 1: Ingestion & Feature Store

1. **Ingestion Trigger**: Daily cron executes parser `uv run python src/wc2026/ingest/elo.py`.
2. **Raw Parse**: Scrapes rating numbers from `eloratings.net` and resolves team names via the crosswalk mapping.
3. **Database Write**: Appends rows to the `elo_timeline` table in `features.db` ([ADR-0002](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0002-storage-stack-duckdb-parquet.md)):
   ```sql
   INSERT INTO elo_timeline (team, date, elo, is_reliable, knowable_at)
   VALUES ('Mexico', '2026-07-03 00:00:00', 1330.0, true, '2026-07-03 00:00:00');
   ```

---

## Phase 2: Feature Engineering & Point-in-Time Gating

1. **Prediction Query**: Scheduled script queries prediction values 2 hours before kickoff (`as_of_ts = 2026-07-03 14:00:00` for a 16:00 match kickoff).
2. **PIT Filter Execution**: The feature store queries current Elo ratings:
   ```sql
   SELECT elo FROM elo_timeline
   WHERE team = 'Mexico' AND knowable_at <= '2026-07-03 14:00:00'
   ORDER BY date DESC LIMIT 1;
   ```
3. **Derived Feature Math**: Extracts target ratings (Elo Mexico = 1330.0, Elo USA = 1297.4):
   $$
   \text{elo\_diff} = 1330.0 - 1297.4 = +32.6\text{ points}
   $$

---

## Phase 3: Model Inference & Ensemble Blending

1. **Individual Model Prediction**:
   - **Dixon-Coles Model (M1)**: Estimates goals scoring parameters ($\alpha, \beta, \rho$) walk-forward, yielding expected goal rates:
     $$
     \lambda_{\text{Mexico}} = 1.34,\quad \mu_{\text{USA}} = 1.05
     $$
     Generates a 15×15 bivariate Poisson score matrix (`ScoreDist`). Summing cells representing Mexico Win (home score $>$ away score) yields a probability of **`0.450`**.
   - **Bayesian Hierarchical Model (M3)**: Simulates scorelines using Hamiltonian Monte Carlo (HMC) sampling, yielding a probability of **`0.435`**.
2. **Meta-Model Pooling**:
   - The ensembler reads active weights from [`configs/default.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/default.yaml) (e.g. M1 weight = $0.70$, M3 weight = $0.30$).
   - Computes weighted average:
     $$
     P_{\text{blend}} = (0.70 \times 0.450) + (0.30 \times 0.435) = 0.4455
     $$

---

## Phase 4: Pricing, De-vigging, & Edge Bounds

1. **L2 Orderbook Pull**: Fetches active Kalshi orderbook: Bid = $0.46$, Ask = $0.48$.
2. **De-vigging (Proportional Model)**: Computes de-vigged market consensus:
   $$
   P_{\text{market}} = \frac{0.47}{1.0} = 0.470
   $$
3. **Fair Value Adjustment**: Reads variables from the config schema:
   - Fee: `-0.010` (Kalshi contract transaction cost).
   - Timing: `-0.002` (capital lockup discount).
   - Resolution Risk: `-0.005`.
   - Calculates fair value price:
     $$
     P_{\text{fair}} = 0.4455 - 0.010 - 0.002 - 0.005 = 0.4285
     $$
4. **Edge Check**: Since $P_{\text{fair}} = 0.4285$ is below the best bid ($0.46$), the model identifies a SELL opportunity (the market is overestimating Mexico's chance).
   $$
   \text{Edge} = \text{Bid} - P_{\text{fair}} = 0.460 - 0.4285 = +0.0315\quad (\text{meets } \ge 0.03 \text{ min\_edge limit})
   $$

---

## Phase 5: Ledger Logging

1. **JSON Serialization**: The execution module appends a transaction record block to `data/ledger/ledger.jsonl` ([ADR-0004](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0004-append-only-ledger-hash-chain.md)):
   ```json
   {
     "seq": 142,
     "timestamp": "2026-07-03T14:02:11.890Z",
     "event_type": "trade",
     "payload": {
       "match_id": "MEX_vs_USA_2026-07-03",
       "ticker": "KX-WC26-MEXUSA-WIN",
       "venue": "kalshi",
       "side": "SELL_YES",
       "price": 0.46,
       "qty": 80,
       "edge_after_fees": 0.0315
     },
     "prev_hash": "2f6c91a0c8bf14d2e5a40b90494cf81050ef093a1f107f9c9861df40dfb0b9a5",
     "hash": "b24df08e9d891b00e84b802a4bf475ef9c8112349df0a5160cb7d10e05cb0ba9"
   }
   ```
2. **Hash Chain Linkage**: The value of `"hash"` is a SHA-256 hex digest of sequence, payload, timestamp, and the value of `"prev_hash"`. Modifying any field in this block breaks the tip hash check.
