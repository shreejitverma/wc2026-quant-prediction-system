# ADR-0007: Free-first data access, with clean paid upgrade points

- Status: accepted
- Date: 2026-07-01

## Context

Operator constraint (2026-07-01): legally authorized to trade, but no funded API access yet.
Decision is to start with free sources and plug paid feeds later.
This shapes which inputs Phase 1 can rely on and which are stubbed behind an interface.

## Decision

We will build every data source behind an interface with a free default implementation and an explicit paid upgrade point:

| Need | Free-first source | Paid upgrade point |
|------|-------------------|--------------------|
| International results | Kaggle / martj42 international-results set | — (already sufficient) |
| Team ratings | eloratings.net (World Football Elo) | — |
| Club/player stats | FBref (Opta-backed), StatsBomb open data | StatsBomb/Opta licensed feeds |
| Historical odds (calibration) | football-data.co.uk (club), odds archives | Betfair historical, paid international archives |
| Exchange books | Kalshi public API, Polymarket CLOB/Gamma (read) | authenticated/live trading endpoints |
| Sharp reference | Pinnacle-derived de-vig from odds archives | **Betfair exchange (geo-restricted in US; disabled)** |

`venues.betfair_enabled = false` in config reflects the absence of funded/geo access; the "sharpest reference price" is sourced from Pinnacle-style de-vigging until Betfair is available.

## Alternatives rejected

- **Block on paid feeds** — stalls the entire build for data that free sources cover adequately for calibration and benchmarking.
- **Hardcode free sources without an interface** — makes the eventual paid upgrade a rewrite instead of a config swap.

## Consequences

Phase 1 can proceed now.
Every source has a named, low-friction upgrade path.
Failure mode avoided: coupling model code to a specific free scraper such that paid data later requires surgery.
Note (latency reflex): none of these upgrades is about speed; they are about data *quality and coverage*, which is where accuracy actually lives.
