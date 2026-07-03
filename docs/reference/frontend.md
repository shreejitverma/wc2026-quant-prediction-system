# Frontend Operator Console Reference

The frontend console is a desktop-first quantitative workstation built as a Vite React Single Page Application (SPA), styled with Tailwind CSS v4.

---

## 1. Frontend Architecture & State Flow

The UI decouples network synchronization and rendering to maintain a high-frequency layout without dropping frames.

```
                  ┌──────────────────────┐
                  │   Vite React SPA     │
                  └──────────┬───────────┘
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     Zustand Store     TanStack Query     WebSockets
   (blotter, limits)  (FastAPI polling)  (L2 books, trades)
```

### 1.1 Zustand Store (`src/store/tradingStore.ts`)
Houses transaction records, active positions, and operational parameters:
- `positions`: Map of active contracts, current inventory $q$, and average fill prices.
- `trades`: Chronological record of virtual/live execution fills.
- `limits`: Holds risk parameters loaded from Pydantic config (e.g. `maxPositionSize`, `bankroll`).

### 1.2 TanStack Query Polling (`src/lib/api.ts`)
Coordinates background HTTP synchronization with the FastAPI backend:
- **Health & Freshness**: Polled every 5 seconds.
- **Match Predictions**: Polled every 30 seconds (updates when cron runs or news events occur).
- **Runs Log**: Polled every 10 seconds.

---

## 2. Real-Time WebSocket Channel Layout

The console establishes a persistent TCP connection to `ws://localhost:8000/api/v1/ws`.

| Topic Pattern | Payload Type | Broadcast Frequency | Trigger |
| :--- | :--- | :--- | :--- |
| `markets.L2.{ticker}` | `L2BookUpdate` | High frequency ($< 500\text{ms}$) | Every bid/ask change in the exchange orderbook. |
| `execution.fills` | `TradeFill` | Event-driven | Triggers immediately when a trade executes or fills. |
| `ops.kill_switch` | `KillState` | Event-driven | Triggers immediately upon kill-switch activation. |
| `ops.alerts` | `AlertEvent` | Event-driven | Emitted immediately when a new alert is spawned. |

---

## 3. UI Screen & Visualization Reference

The console is structured into four main operational pages:

### 3.1 CommandCenter (`src/pages/CommandCenter.tsx`)
- **Key Metrics Panel**: Net Asset Value (NAV), Daily P&L, Active Quote Counts, and System Health.
- **Health Grid**: Color-coded connectivity status (FastAPI backend, Ingest loop, Kalshi API, Polymarket API).
- **Blotter Table**: Displays active positions, average cost, mark-to-market value, and current inventory bounds.

### 3.2 Matchday (`src/pages/Matchday.tsx`)
Provides a comprehensive overview of a single fixture before quoting:
- **Rest & Context Cards**: Displays altitude delta, kickoff temperature, and rest days for both teams.
- **Form Timeline**: Chronological Elo ratings updates over the past 5 matches.
- **Scoreline Heatmap Matrix**: Renders a 15×15 SVG grid representing the ensembler's joint probability distribution, with color intensity mapping to cell probability.

### 3.3 Opportunities (`src/pages/Opportunities.tsx`)
- **Arbitrage Cards**: Highlights contract tickers where the model's Fair Value interval falls outside the exchange's L2 Bid/Ask spread, sorted by Expected Value (EV).
- **Trade Trigger Button**: Submits trade requests to the execution engine.

### 3.4 Ledger (`src/pages/Ledger.tsx`)
- **Ledger Verification Status**: Shows a checkmark if the SHA-256 chain is valid, and displays the genesis hash and tip hash.
- **Ledger Stream**: Logs chronological events read from `ledger.jsonl`.

---

## 4. Emergency Kill-Switch Interface

The UI includes a prominent emergency **KILL SWITCH** panel accessible from any page.
- **Behavior**: Clicking the kill switch halts all quotes.
- **Safety Lock**: To prevent accidental activation, the operator must type the exact confirmation phrase `PULL_ALL_QUOTES` before the submit button unlocks.
- **Backend Trigger**: Sends a `POST /api/v1/commands/kill-switch` request, triggering immediate quote cancellations on Kalshi and Polymarket.
