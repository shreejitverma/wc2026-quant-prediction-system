# Model Cards — Implementation Catalog

A **model card** documents what a model assumes, what it can and cannot capture, and its evaluation history. A model without a card is not allowed into the ensemble.

> **Deep-dive reference**: For complete mathematical equations, statistical priors, hyperparameters, and detailed failure mode analysis, see **[docs/models.md](../models.md)**. This file is the quick-reference index.

---

## What is a Model Card?

A model card answers four questions:
1. **What signal does this model use?** (input features and their PIT timestamp requirements)
2. **What mathematical structure does it assume?** (the form of the likelihood function)
3. **When should this model be trusted?** (conditions under which it performs well)
4. **When should this model be distrusted or down-weighted?** (failure modes)

Every model is an imperfect approximation of reality. The ensemble only works well if we know *which approximations each model makes* so we can combine them intelligently.

---

## Ensemble Design Rationale

The six models are not redundant copies of the same approach. They are deliberately **orthogonal information sources**:

| Information Source | Best Model | Rationale |
|--------------------|-----------|-----------|
| Historical match results (long-run team quality) | M1 Dixon-Coles | Maximally efficient use of low-noise result data |
| Recent form / trend | M2 State-Space | Kalman-style filter captures momentum without overfitting |
| Uncertainty quantification | M3 Bayesian | Full posterior distributions, not point estimates |
| Lineup-conditional team strength | M4 Player-Agg | Connects team-level prediction to squad-level reality |
| Non-linear feature interactions | M5 LightGBM | Tree gradient boosting captures complex feature interactions |
| Market price as signal | M6 Market-Implied | Sharp money already incorporates information we don't have |

When these six models disagree, it is informative (high uncertainty). When they agree, the ensemble's confidence is high. The Meta-Ensembler (BFGS log-opinion pooling) learns how much to trust each model based on historical calibration.

---

## Implemented Models Catalog

| ID | Model Name | Source File | Status | Primary Input | Output |
|----|-----------|------------|--------|--------------|--------|
| M1 | Dixon-Coles Bivariate Poisson | [dixon_coles.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/dixon_coles.py) | ✅ **Built** | Historical result scorelines | `ScoreDist` (15×15 matrix) + `ρ` low-score correction |
| M2 | Dynamic State-Space Ratings | [state_space.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/state_space.py) | ✅ **Built** | Rolling result time-series | Trending attack/defense ratings + `ScoreDist` |
| M3 | Bayesian Hierarchical Goals | [hierarchical.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/hierarchical.py) | ✅ **Built** | Historical results + priors | Full posterior `ScoreDist` distribution |
| M4 | Player-Aggregation Team Strength | [player_agg.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/player_agg.py) | ✅ **Built** (activates at lineup drop) | Player-level xG/xGA stats + confirmed XI | Lineup-conditional `ScoreDist` |
| M5 | Gradient Boosting (LightGBM) | [gbm.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/gbm.py) | ✅ **Built** | Multi-feature matrix (Elo, form, venue, rest) | Poisson goal rate predictions → `ScoreDist` |
| M6 | Market-Implied Bivariate Poisson | [market_implied.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/market_implied.py) | ✅ **Built** | De-vigged exchange prices | Inverted `ScoreDist` from market consensus |
| ME | Meta-Ensembler (BFGS Log-Opinion Pooling) | [meta_ensemble.py](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/meta_ensemble.py) | ✅ **Built** | M1–M6 `ScoreDist` matrices | Single canonical `ScoreDist` + ensemble weights |

---

## Key Failure Modes Summary

> Complete, detailed failure modes are documented in `docs/models.md`. This is a quick-reference summary.

| Model | Critical Failure Mode | Mitigation |
|-------|----------------------|-----------|
| **M1** | "Dead rubbers" — matches where team motivation is absent (e.g., a team already eliminated playing their last group game). Historical result data does not capture motivation. | Down-weight M1 in group stage final round matches where advancement is already decided. |
| **M2** | Mean-reversion lag — after a shock (key player injured), the state-space filter requires several matches to fully update ratings. | M4 (player-aggregation) compensates for this at lineup drop. |
| **M3** | MCMC warmup cost (~45 seconds). Cannot be re-run in real-time. | Run M3 on a pre-match cycle; cache results and warm-update with new information. |
| **M4** | Entirely dependent on accurate lineup data. Expected XI ≠ Confirmed XI. If FBref lineup source is wrong, M4 can severely misprice a match. | Validate confirmed XI against 2+ sources before activating M4 at full weight. |
| **M5** | Overfits to recent tournament patterns (e.g., if European teams dominated the last 4 WCs, GBM over-weights European teams for WC 2026 specifically). | Regularization (L1/L2), tree depth limits, and cross-tournament validation required. |
| **M6** | Circular when used naively: if the market is wrong, M6 will faithfully reflect the error back. | M6 is a *prior*, not a gold standard. It is down-weighted when the ensemble's other models strongly disagree. |
| **ME** | BFGS ensemble weights can collapse all weight onto one model if others are poorly calibrated on recent data. | Monitor weight entropy; alert if any single model weight exceeds 60%. |

---

## Model Integration Status

- All 6 models output a common `ScoreDist` interface (15×15 probability matrix + metadata).
- All 6 models respect the PIT gate: features are accessed via `PointInTimeStore.as_of(kickoff_ts)`.
- All 6 models log their outputs to the hash-chained ledger at prediction time.
- The Meta-Ensembler recombines M1–M6 using BFGS-optimized Log-Opinion Pooling weights.
