# System Glossary

This glossary defines core terminology spanning soccer statistics, tournament formatting, market microstructure, and system architecture.

---

## 1. Soccer & Tournament Terms

* **Lineup Window**: The period 75 minutes prior to kickoff when team sheets are officially registered. In this window, the ensembler switches weights to model **M4** (Player Aggregation) to capture player-specific adjustments.
* **Best Third-Placed**: The tournament qualification rule where the 8 highest-performing third-place teams (ranked by points, goal difference, and goals scored) join the top 2 teams from each of the 12 groups in the Round of 32.
* **Elo Rating**: A relative strength metric calculated walk-forward by comparing expected outcomes with actual match goals and score deltas.

---

## 2. Market Microstructure Terms

* **De-vigging**: The mathematical process of stripping the implied probability inflation (overround/vig) from bookmaker odds or exchange orderbooks to estimate the market's true underlying probability.
* **Shin Model**: A de-vigging model that solves for the probability parameter by accounting for a fraction of "informed traders" in the orderbook.
* **Closing Line Value (CLV)**: The primary measure of execution quality. Defined as the difference between the fill price and the de-vigged closing price at kickoff. A positive CLV indicates transaction alpha.
* **L2 Orderbook Depth**: The array of available contract bid/ask volumes at distinct limit price ticks.
* **Reservation Price**: The price at which a market-maker is indifferent to holding inventory, calculated by adjusting the fair value to account for inventory risk.

---

## 3. System Architecture Terms

* **Honesty Harness**: The automated runtime safety checking suite that monitors ledger integrity, point-in-time constraints, and risk limits.
* **Point-in-Time (PIT) Gate**: The data store query rule asserting `knowable_at <= as_of_ts`. Prevents lookahead bias by hiding match information that was not public at the specified timestamp.
* **Provenance Envelope**: The JSON wrapper schema containing active git commits, config hashes, and data hashes, guaranteeing that every API output is fully reproducible.
* **Reconciliation Break**: A runtime error raised when the virtual ledger position inventory differs from the actual position balance retrieved from the exchange APIs.
