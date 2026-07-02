# Data Contracts

One file per data source, describing exactly what we ingest and its quirks.
A data contract is the agreement between the messy outside world and our clean internal schema.
Every field that later becomes a feature must be traceable to a contract here.

Populated in Phase 1 as sources are wired.
Use `_template.md` for each new source.

## Non-negotiable columns for every source

- **UTC convention**: every timestamp is timezone-aware UTC; the contract states how the source's native timezone was converted.
- **`knowable_at`**: for every field, when did this datum become observable to us? This feeds the point-in-time gate (ADR-0005). A field with an unclear `knowable_at` is a leak risk and must be flagged.
- **Cadence & freshness**: how often the source updates, and the freshness metadata we attach.
- **Idempotency key**: how we dedupe re-fetches.

## Planned sources (Phase 1)

| Source | Tier | Contract file |
|--------|------|---------------|
| martj42 international results | 1 | `results_international.md` |
| eloratings.net | 1 | `elo_ratings.md` |
| football-data.co.uk odds | 1/3 | `odds_footballdata.md` |
| Kalshi markets/books/trades | 3 | `kalshi.md` |
| Polymarket CLOB/Gamma | 3 | `polymarket.md` |
| FBref / StatsBomb player stats | 2 | `player_stats.md` |
| Venue / weather / referee | 4 | `context.md` |
| Beat-source news (LLM-extracted) | 5 | `news_events.md` |
