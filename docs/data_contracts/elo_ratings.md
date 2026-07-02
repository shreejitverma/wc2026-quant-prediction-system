# Data Contract: World Football Elo Ratings (eloratings.net)

- Tier: 1
- Access: free (public scraping; polite)
- URL: https://www.eloratings.net/World.tsv
- robots.txt / ToS: No explicit restriction on World.tsv; polite 1 request/day
- Rate limit & backoff policy: 1 request/day, 2-second minimum interval
- Idempotency key: `{date}/world.tsv`
- Native timezone: N/A (ratings are a point-in-time snapshot, no timestamps)

## Schema (TSV, no header, column layout confirmed 2026-07-01)

| Col | Field | Type | `knowable_at` | Notes |
|-----|-------|------|---------------|-------|
| 0 | rank | int | Fetch time | Current world rank |
| 1 | prev_rank | int | Fetch time | Previous week's rank |
| 2 | team_code | str | Fetch time | 2-letter code (AR, ES, EN, ...) |
| 3 | elo | int | Fetch time | Current Elo rating |
| 4 | region | int | Fetch time | Region ID (encoding not fully documented) |
| 5 | elo_max | int | Fetch time | All-time highest Elo |
| 6 | elo_max_rank | int | Fetch time | World rank at elo_max |
| 7 | elo_max_year | int | Fetch time | Year of elo_max |
| 8 | elo_min_rank | int | Fetch time | World rank at elo_min |
| 9 | elo_min | int | Fetch time | All-time lowest Elo |
| 10-21 | change pairs | int | Fetch time | Pairs (rank_delta, elo_delta) for 1w/1m/3m/6m/1y/5y |

## Why Elo > FIFA rankings

Hvattum & Arntzen (2010) "Using ELO ratings for match result prediction in association football" demonstrates that Elo-family ratings materially outperform FIFA's points formula as match outcome predictors. The core reason: Elo applies a paired Bayesian update after every match using the actual outcome and expected probability; FIFA uses a decay-weighted points accumulation that underweights outcome margins and overweights confederation-level adjustments. Elo self-corrects; FIFA points drift.

FIFA rankings are retained as a reference (they determine pot seedings and WC qualification), but should not be used as prediction features.

## Cadence & freshness

- Updated by eloratings.net roughly weekly, and after major tournament matches.
- We fetch daily during live tournaments so ratings reflect recent results.

## Known quirks & failure modes

- **2-letter codes are not ISO 3166 alpha-2**: "EN" = England (ISO: GB-ENG), "KO" = South Korea (ISO: KR). Always resolve through `TeamCrosswalk`.
- **No historical per-match Elo**: the World.tsv gives current standings only, not a history of rating changes. For historical Elo values (needed for training), per-team pages or a separate computation from the results history is required (Phase 2 feature store will derive this from martj42 + the Elo formula).
- **Rating staleness during international breaks**: ratings between major tournaments may be months old; the fetch date tells us which vintage we trained on.

## Leakage notes

- The current Elo snapshot is knowable at fetch time. For historical backtesting, only use the Elo value that was observable *before* the match being predicted — this requires reconstructing Elo from the results history rather than using today's fetched values. The Phase 2 feature store handles this via `get_features(match_id, as_of_ts)`.
- Never use the current fetched Elo to predict a historical match: this is the canonical look-ahead bias for ratings-based models.
