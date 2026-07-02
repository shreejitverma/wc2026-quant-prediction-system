# Data Contract: International Football Results (martj42)

- Tier: 1
- Access: free (public GitHub)
- URL: https://raw.githubusercontent.com/martj42/international_results/master/results.csv
- robots.txt / ToS: GitHub raw content; polite access, no crawling
- Rate limit & backoff policy: 1 request/day, no auth required
- Idempotency key: `{date}/results.csv` (one file per fetch date)
- Native timezone: dates only (no time), treated as UTC midnight

## Schema

| Field | Type | Units | `knowable_at` | Notes |
|-------|------|-------|---------------|-------|
| date | DATE | - | Date of fetch (conservative) | Match date only, no kick-off time |
| home_team | str | - | Date of fetch | Free-text names; run through crosswalk |
| away_team | str | - | Date of fetch | Free-text names; run through crosswalk |
| home_score | int or null | goals | After final whistle | Null for scheduled/unplayed matches |
| away_score | int or null | goals | After final whistle | Null for scheduled/unplayed matches |
| tournament | str | - | Date of fetch | Used to derive `is_competitive` |
| city | str | - | Date of fetch | Venue city |
| country | str | - | Date of fetch | Venue country (not necessarily home team's) |
| neutral | bool | - | Date of fetch | TRUE = venue was neutral |

## Derived field

`is_competitive`: True if tournament string contains any of the `_COMPETITIVE_KEYWORDS` list. Friendlies are retained in raw; models use this flag to weight matches.

## Cadence & freshness

- Updated after every international match day.
- Fetched once per day by `make daily`; the fetch date partitions the raw store.
- Gap/duplicate detection: row count logged per fetch; alert if < previous.

## Known quirks & failure modes

- **Team name drift**: "South Korea" vs "Korea Republic" across vintages. Always resolve through `TeamCrosswalk`.
- **Retroactive corrections**: walkovers, disqualifications, replay results may change historical rows. The raw file is dated so training data is reproducible; model calibration uses the *fetch-date* version, not an idealized "true" history.
- **No kick-off time**: match date only, which makes `knowable_at` coarse (midnight UTC is conservative). For live tournament matches, supplement with venue/kickoff data from the context tier.
- **Future matches have null scores**: `home_score`/`away_score` are null for scheduled matches in the file. Parsers skip null-score rows when computing actual outcomes.

## Leakage notes

- `home_score` and `away_score` are **post-match facts**. Their `knowable_at` is "after the final whistle," not the match date. Never use scores as input features for pre-match prediction in any training window that includes those matches.
- The tournament name is knowable before kickoff (it is scheduled information); it is safe as a pre-match feature.
