# Data Contracts

A **data contract** is the formal agreement between the messy outside world and our clean internal schema. It specifies exactly what fields we ingest from each source, what their types and units are, how we timestamp them, and critically — **when each datum became observable** (the `knowable_at` field that feeds the Point-In-Time gate).

> **Why this matters**: The `knowable_at` field is not a technicality. It is the *difference between a legitimate backtest and a backtest that lies*. If we join a player's transfer value (scraped "today") onto a historical match from 3 years ago, we have injected look-ahead leakage. The contract forces us to think carefully about when each fact was truly observable. See ADR-0005 for the full rationale.

---

## Non-Negotiable Fields for Every Source

Every data contract must define the following for every field:

| Field | Requirement | Why |
|-------|-------------|-----|
| **UTC convention** | All timestamps are timezone-aware UTC. The contract states how the source's native timezone was converted. | Naive datetimes silently corrupt time-order comparisons and PIT filters. |
| **`knowable_at`** | For every field: when was this datum *observable to us*? This is distinct from when it *happened*. A match result is knowable at the final whistle, not at kickoff. | Feeds the PIT gate (ADR-0005). A field with an unclear `knowable_at` is a **leak risk** and must be flagged before use. |
| **Cadence & Freshness** | How often does the source update? What is the maximum expected staleness? | Stale features produce stale predictions. The system's health endpoint monitors freshness lag. |
| **Idempotency Key** | How do we detect and discard duplicate fetches? | Re-fetching the same data twice should be a no-op. Duplicates corrupt model training sets. |

---

## Data Tier Classification

We categorize incoming data into four tiers based on **velocity** (how fast it changes) and **reliability** (how structured and authoritative the source is):

| Tier | Description | Velocity | Example Sources |
|------|-------------|----------|----------------|
| **Tier 1** | Historical results and established ratings. Changes only when new matches are played. | Daily | FBref historical results, EloRatings.net, international results database |
| **Tier 2** | Player-level squad and performance data. Changes during transfer windows and weekly match cycles. | Weekly | FBref/StatsBomb xG, squad depth, player availability |
| **Tier 3** | Live prediction market orderbooks. Changes every second. | Real-time (WebSocket) | Kalshi CLOB, Polymarket CLOB/Gamma, sharp books |
| **Tier 4** | Contextual match metadata. Changes rarely; verified before each match. | Per-match | Venue coordinates, altitude, weather forecast, referee assignment |

The data ingestion pipeline processes each tier with appropriate fetch cadences:
- **Tier 1**: Nightly cron job.
- **Tier 2**: 6-hour intervals during tournament.
- **Tier 3**: Persistent WebSocket connections with automatic reconnection.
- **Tier 4**: Manual verification + automated lookup 24h before kickoff.

---

## Implemented Data Contracts

| Source | Tier | Contract File | Status |
|--------|------|---------------|--------|
| martj42 international results (GitHub) | 1 | [results_international.md](results_international.md) | ✅ Implemented |
| EloRatings.net | 1 | [elo_ratings.md](elo_ratings.md) | ✅ Implemented |
| Kalshi CLOB markets/books/trades | 3 | [kalshi.md](kalshi.md) | ✅ Implemented |
| Polymarket CLOB/Gamma API | 3 | [polymarket.md](polymarket.md) | ✅ Implemented |
| football-data.co.uk odds | 1/3 | `odds_footballdata.md` | 🔄 Planned Phase 1 |
| FBref / StatsBomb player stats | 2 | `player_stats.md` | 🔄 Planned Phase 2 |
| Venue / altitude / weather / referee | 4 | `context.md` | 🔄 Planned Phase 3 |
| Beat-source news (LLM-extracted signals) | 5 | `news_events.md` | 🔄 Planned Phase 4 |

---

## The `knowable_at` vs `occurred_at` Distinction

This distinction is the most commonly misunderstood concept in sports quantitative modeling.

**Example: A red card shown in the 15th minute of a match.**
- `occurred_at`: The timestamp of the red card event (e.g., `2026-06-15T15:15:00Z`)
- `knowable_at`: The timestamp when we *received and processed* the red card signal from our data source (e.g., `2026-06-15T15:17:30Z` — 2.5 minutes later, after the API poll or websocket push)

When backtesting the *first half* of that same match, the PIT gate will correctly **exclude** the red card feature because it was not knowable until `15:17:30Z`, which is *after* the simulated query time. Using the red card to predict goals scored in the first half of that same match would be pure leakage.

Use `_template.md` when adding a new data source contract.
