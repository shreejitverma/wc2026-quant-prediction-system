# Model Evaluation Dossier

This document compiles the quantitative performance reports, pre-registered experiment statuses, and historical backtest details for the active modeling suite.

---

## 1. Pre-Registered Experiment Summary

Before promotion to the live production configuration, all models must pass through the frozen pre-registration gate system ([PR-2026 Index](../preregistrations/README.md)).

| Experiment ID | Target Metric | Target Threshold | Realized Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`PR-2026-M1-DC`** | Out-of-Sample Log-Loss | $< 0.880$ | **`0.831`** | **PASSED** |
| **`PR-2026-M3-HMC`**| Expected Calibration Error (ECE) | $< 0.050$ | **`0.041`** | **PASSED** |
| **`PR-2026-M5-GBM`**| Brier Score | $< 0.580$ | **`0.592`** | **FAILED** (Rejected altitude bias) |

---

## 2. Walk-Forward Backtest Performance

The following table summarizes the rolling walk-forward backtest results over the historical 2018–2022 international cycles (evaluated on $N = 1,420$ fixtures):

| Model / Configuration | Mean Log-Loss | Brier Score | ECE |
| :--- | :--- | :--- | :--- |
| **Naive Baseline (1/3 split)** | $1.098$ | $0.667$ | $0.240$ |
| **Market Odds Implied (De-vigged)** | $0.824$ | $0.512$ | $0.021$ |
| **M1: Dixon-Coles Poisson** | $0.842$ | $0.528$ | $0.048$ |
| **M3: Bayesian Hierarchical (HMC)**| $0.838$ | $0.524$ | $0.041$ |
| **Ensemble (0.7 M1 + 0.3 M3)** | **`0.829`** | **`0.518`** | **`0.035`** |

---

## 3. Paper Trading Edge (CLV Record)

Over the mock/paper trading run spanning the initial qualification cycle ($N = 168$ trades), the ensembler recorded the following execution metrics:
- **Mean Closing Line Value (CLV)**: **`+0.84%`**
  *Significance*: Under a standard $t$-test, $p < 0.01$, confirming the model is identifying contract pricing discrepancies that systematically revert to the closing line.
- **Realized Virtual Sharpe Ratio**: **`1.42`** (adjusted for 120-second feed-latency intervals).

---

## 4. Sources of Optimism Bias

While the backtest pipeline implements strict Point-in-Time gating, operators should remain aware of the following residual sources of optimism:
* **Reporting Delays in Elo Scores**: Historical ratings from `eloratings.net` are archived on a daily cadence. The backtester assumes Elo scores computed at midnight were knowable for a match played at 15:00 on that day.
* **Match Venue Altitude Simplification**: The altitude database assumes uniform conditions for all fixtures played within a city's municipal area. It does not account for localized microclimatic variations.
