# Configuration Schema Reference

The system configuration is loaded from YAML files (default: [`configs/default.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/default.yaml)) and validated at startup using Pydantic schemas in [`src/wc2026/config.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/config.py).

---

## 1. Global Configuration Options

The top-level configuration class `AppConfig` has `extra = "forbid"` enabled. Specifying any unvalidated keys in the YAML file raises a validation error, preventing execution.

| Key | Type | Default | Rationale / Behavior |
| :--- | :--- | :--- | :--- |
| `mode` | `Literal["paper", "live"]` | `"paper"` | Operational mode. Live execution blocks unless explicitly set to `"live"`. |
| `db_path` | `str` | `"data/processed/features.db"` | Absolute or relative path to the local DuckDB database. |
| `raw_store_dir` | `str` | `"data/raw"` | Root directory where original API/scraper payloads are archived. |
| `ledger_path` | `str` | `"data/ledger/ledger.jsonl"` | File path of the hash-chained, append-only audit trail. |

---

## 2. Subsystem Configurations

### 2.1 The `risk` Block
Controls position sizing and allocation parameters.

| Key | Type | Default | Rationale / Behavior |
| :--- | :--- | :--- | :--- |
| `bankroll_usd` | `float` | `5000.0` | Total capital base used for Kelly sizing calculations. |
| `kelly_fraction` | `float` | `0.25` | Fractional Kelly sizing multiplier (quarter-Kelly) to protect against model errors. |
| `max_position_per_event_usd` | `float` | `100.0` | Maximum absolute position exposure in USD on any single contract event. |
| `max_portfolio_drawdown_pct` | `float` | `0.20` | Portfolio-level stop-out limit. Halts all trading if net drawdown exceeds this fraction. |
| `min_edge` | `float` | `0.03` | Minimum post-fee model edge (in cents/percent) required to submit a quote. |

---

### 2.2 The `kill_switch` Block
Controls automated safety pull commands.

| Key | Type | Default | Rationale / Behavior |
| :--- | :--- | :--- | :--- |
| `enabled` | `bool` | `true` | Enables/disables automated safety monitoring loops. |
| `max_data_staleness_seconds` | `int` | `120` | Timeout threshold. If data feeds go stale for longer than this, all quotes are cancelled. |
| `pnl_stop_usd` | `float` | `250.0` | Daily loss limit. Halts trading for the day if net realized loss hits this dollar amount. |
| `reconcile_every_cycle` | `bool` | `true` | Enforces position reconciliation check against exchange states on every execution pass. |

---

### 2.3 The `venues` Block
Enables or disables individual exchange adapters.

| Key | Type | Default | Rationale / Behavior |
| :--- | :--- | :--- | :--- |
| `kalshi_enabled` | `bool` | `true` | Enables Kalshi REST and L2 WebSocket orderbook streams. |
| `polymarket_enabled` | `bool` | `true` | Enables Polymarket Gamma and CLOB wrappers. |
| `betfair_enabled` | `bool` | `false` | Disabled due to US geo-restrictions and funding boundaries. |

---

### 2.4 The `news` Block
Configures news intelligence pipeline fences.

| Key | Type | Default | Rationale / Behavior |
| :--- | :--- | :--- | :--- |
| `autonomous_trading` | `Literal[False]` | `False` | **The configuration fence**. Prevents LLM news signals from directly placing orders without human confirmation. |
| `review_threshold_quote_move` | `float` | `0.02` | Extracted facts implying a quote adjustment $\ge 2\%$ are held in the manual review queue. |
