# System Discrepancies: Code vs. Intended Design

This document serves as the official registry of architectural drifts and structural mismatches between the quantitative design specifications (from the master plan and ADRs) and the actual implementation in the codebase.

---

## 1. M4 Player-Aggregation Model is a Mock Skeleton

- **Location**: [`src/wc2026/models/player_agg.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/player_agg.py)
- **Intended Design**: A bottom-up team strength predictor that aggregates individual club-season player statistics (Expected Goals/90, Expected Assists/90 from FBref) weighted by their minutes-played and league quality multipliers. Upon the release of the official lineup (T-60m), this model should dynamically re-simulate the match based on the actual starting XI.
- **Actual Code**: The `fit()` method is a `pass` no-op. The `predict_match()` method ignores features and returns a hardcoded expectation of `1.1` goals for both teams, which is then fed into a standard independent Poisson distribution.
- **Mitigation/Resolution**: The model must remain labeled as a **mock skeleton** in the model catalog. Live ensembling weight schedules must down-weight M4 to zero until a real ingestion parser for Tier 2 player statistics and lineups is wired into the Feature Store.

---

## 2. Heuristic Ticker-Prefix Contract Mapping

- **Location**: [`src/wc2026/pricing/mapper.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/pricing/mapper.py)
- **Intended Design**: An LLM-assisted contract parser that reads the exchange-specific resolution language (`rules_primary` from Kalshi or `description` from Polymarket) to extract the settlement event, mapping it automatically with a human-confirmation queue to protect against resolution discrepancies (e.g., "advances" vs "wins in 90 minutes").
- **Actual Code**: The mapping is performed via static prefix check string operations on the ticker string itself:
  ```python
  if ticker.startswith("KXWCADVANCE-"):
      # ...
  ```
  It has no capability to query or read exchange rules/description strings, nor does it maintain a human-confirmation queue.
- **Mitigation/Resolution**: Mappings must be hand-verified by the operator and hardcoded into configuration files. Any ticker shape not matching the existing hardcoded prefixes will fall back to `EventType.UNKNOWN` and will be automatically quarantined from the quoting engine.

---

## 3. Mock CLI Orchestrator (`cron.py`)

- **Location**: [`src/wc2026/ops/cron.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ops/cron.py)
- **Intended Design**: A CLI-orchestrated event loop that coordinates the full pipeline on a schedule: ingestion (fetch -> parse) -> update Feature Store -> refit models -> run 100k-path tournament simulations -> compute fair values -> query L2 books -> run Avellaneda-Stoikov quoting -> execute trades.
- **Actual Code**: The command-line groups `backtest`, `live`, and `coherence` are empty shells that print simulated logging text using `click.echo()`. They do not instantiate or call any of the underlying modules.
- **Mitigation/Resolution**: To execute the pipeline, the operator must write explicit scripting or call individual Python entry points manually. We document the manual command sequence in the Operational Runbooks rather than relying on `cron.py` for execution.

---

## 4. Avellaneda-Stoikov Inventory Scaling Mismatch

- **Location**: [`src/wc2026/execution/quoting.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/execution/quoting.py)
- **Intended Design**: Adjust quoting spreads and reservation prices based on portfolio inventory to manage risk.
- **Actual Code**: The reservation price update step is implemented as:
  $$
  r = \text{fair\_value} - \gamma \cdot \text{variance} \cdot \text{inventory} \cdot \text{time\_to\_settlement}
  $$
  For binary contracts, price is strictly bounded in the range $[0.00, 1.00]$ dollars. However, the `inventory` parameter represents a raw count of contracts (e.g. `+100` contracts). If inventory is high, $\gamma \cdot \text{variance} \cdot \text{inventory}$ scales into the double-digits, pushing the reservation price $r$ completely out-of-bounds (which is then clamped to the boundaries $[0.01, 0.99]$).
- **Mitigation/Resolution**: The `inventory` parameter must be scaled by contract value (e.g. contract size in USDC/100) or $\gamma$ must be set to an extremely small value (e.g. $0.0001$) to prevent inventory shifts from dominating the midpoint price calculation.
