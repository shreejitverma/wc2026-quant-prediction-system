# FastAPI OpenAPI Reference

The system backend exposes a FastAPI REST and WebSocket interface running by default on `http://localhost:8000`. Every response is wrapped in a standard **[Provenance Envelope](../adr/0012-api-provenance-envelope.md)** payload.

---

## 1. The Response Envelope Schema

Every REST response conforms to the following generic TypeScript type:

```typescript
interface Envelope<T> {
  // The query metadata envelope
  provenance: {
    git_commit: string;       # Current HEAD commit hash (7-char)
    config_hash: string;      # SHA-256 hash of active YAML config
    data_hash: string;        # SHA-256 hash of underlying feature database state
    feature_hash: string;     # SHA-256 hash of derived features table
    is_mock: boolean;         # True if system is running in mock/demo mode
    generated_at_utc: string; # ISO 8601 UTC timestamp of response generation
  };
  data: T;                    # The actual payload content
}
```

---

## 2. API Endpoints Catalog

### 2.1 System Monitoring & Status
- **`GET /api/v1/health`**
  - *Returns*: `Envelope<HealthData>`
  - *Description*: Core health check of the platform. Verifies database connectivity, data staleness thresholds, and current git provenance.
- **`GET /api/v1/ops/freshness`**
  - *Returns*: `Envelope<OpsFreshness>`
  - *Description*: Returns the last update timestamp of all ingestion directories, flagging any feed that has breached the maximum allowed staleness boundary (120 seconds).
- **`GET /api/v1/alerts`**
  - *Returns*: `Envelope<AlertsPage>`
  - *Description*: Returns active system alerts, including data feed disconnects, risk violations, or API errors.
- **`POST /api/v1/alerts/{alert_id}/ack`**
  - *Returns*: `Envelope<CommandResult>`
  - *Description*: Acknowledges and clears an active alert by ID.

### 2.2 Ledger & Run Logs
- **`GET /api/v1/ledger`**
  - *Returns*: `Envelope<LedgerPage>`
  - *Description*: Paginated access to the append-only JSONL ledger.
- **`GET /api/v1/ledger/verify`**
  - *Returns*: `Envelope<LedgerVerification>`
  - *Description*: Runs `verify_chain()` to audit the entire SHA-256 hash chain and returns a boolean status flag.
- **`GET /api/v1/runs`**
  - *Returns*: `Envelope<RunsPage>`
  - *Description*: List of all historical training run records from the local runs log.
- **`GET /api/v1/runs/{run_id}`**
  - *Returns*: `Envelope<RunOut>`
  - *Description*: Detail of a specific training run, including hyperparameter config and validation log-loss metrics.

### 2.3 Prediction & Simulation
- **`GET /api/v1/matches`**
  - *Returns*: `Envelope<list[MatchPrediction]>`
  - *Description*: Returns predictions for all matches in the current cycle, including model weights and blended team win/draw/loss probabilities.
- **`GET /api/v1/matches/{match_id}`**
  - *Returns*: `Envelope<MatchDetail>`
  - *Description*: Full match details, including rest days, venue altitude, and the 15×15 joint score distribution matrix (`ScoreDist`).
- **`GET /api/v1/matches/{match_id}/timeline`**
  - *Returns*: `Envelope<MatchTimeline>`
  - *Description*: Reconstructs the historical Elo and scoreline adjustments for the two competing teams.
- **`GET /api/v1/tournament`**
  - *Returns*: `Envelope<TournamentState>`
  - *Description*: Current simulated marginal probabilities for tournament outcomes (group winner, reaches R16/QF/SF/Final, wins tournament) across all 48 teams.
- **`POST /api/v1/sim/query`**
  - *Returns*: `Envelope<SimQueryResult>`
  - *Description*: Executes conditional queries on the simulator (e.g. "What is the probability of England reaching the final *given* France is eliminated in the group stage?").

### 2.4 Arbitrage & Quoting
- **`GET /api/v1/opportunities`**
  - *Returns*: `Envelope<list[MarketOpportunity]>`
  - *Description*: Active edges across Kalshi and Polymarket ranked by Expected Value (EV).
- **`GET /api/v1/coherence`**
  - *Returns*: `Envelope<CoherenceReport>`
  - *Description*: Returns list of internal bracket coherence violations (e.g. sum of group advancement probabilities $\ne$ advancement slot totals).
- **`GET /api/v1/console/{ticker}`**
  - *Returns*: `Envelope<ConsoleState>`
  - *Description*: Reservation price and quoting spreads for the specified contract ticker, calculated via the Avellaneda-Stoikov model.
- **`GET /api/v1/portfolio`**
  - *Returns*: `Envelope<PortfolioState>`
  - *Description*: Active position inventory, capital allocations, and portfolio variance calculated by the CVXPY optimizer.

### 2.5 Operational Commands
- **`GET /api/v1/commands/state`**
  - *Returns*: `Envelope<CommandStateOut>`
  - *Description*: Returns the status of the global kill switch and quoting pauses.
- **`POST /api/v1/commands/kill-switch`**
  - *Payload*: `{ "confirmation": "PULL_ALL_QUOTES" }`
  - *Returns*: `Envelope<CommandResult>`
  - *Description*: Activates the master kill switch, pulling all quotes on exchanges immediately and halting execution.
- **`POST /api/v1/commands/quoting/{ticker}/pause`**
  - *Returns*: `Envelope<CommandResult>`
  - *Description*: Pauses market-making for a specific contract ticker.
- **`POST /api/v1/commands/quoting/{ticker}/resume`**
  - *Returns*: `Envelope<CommandResult>`
  - *Description*: Resumes market-making for a specific paused contract ticker.

### 2.6 Evaluation & Metrics
- **`GET /api/v1/eval/clv`**
  - *Returns*: `Envelope<ClvReport>`
  - *Description*: Reconstructs Closing Line Value metrics (difference between our quote and eventual closing price) across completed paper/live trades.
- **`GET /api/v1/eval/calibration`**
  - *Returns*: `Envelope<CalibrationReport>`
  - *Description*: Binned probability calibration metrics (Brier Score, ECE) for out-of-sample models.
- **`GET /api/v1/eval/model-race`**
  - *Returns*: `Envelope<ModelRaceReport>`
  - *Description*: Head-to-head Log-Loss model race metrics tracking model alpha.
- **`GET /api/v1/eval/pnl`**
  - *Returns*: `Envelope<PnlReport>`
  - *Description*: Renders equity curve and P&L drawdowns over time.

---

## 3. High-Frequency WebSockets

- **WebSocket URL**: `ws://localhost:8000/api/v1/ws`
- **Cadence**: Broadcasts updates on every orderbook change or incoming transaction.
- **Payload Shape**:
  Every message is a JSON string with a topic routing key:
  ```json
  {
    "topic": "markets.L2.KXWCADVANCE-MEX",
    "data": {
      "bids": [[0.47, 500], [0.46, 1200]],
      "asks": [[0.49, 800], [0.50, 1500]],
      "last_updated": "2026-07-03T08:30:00Z"
    }
  }
  ```
