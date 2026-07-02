# Data Contract: <source name>

- Tier: 1 | 2 | 3 | 4 | 5
- Access: free | paid | scraped
- URL / endpoint:
- robots.txt / ToS notes:
- Rate limit & backoff policy:
- Idempotency key:
- Native timezone -> UTC conversion:

## Schema

| Field | Type | Units | `knowable_at` (when observable) | Notes / quirks |
|-------|------|-------|--------------------------------|----------------|
| | | | | |

## Cadence & freshness

- Update frequency:
- Freshness metadata attached:
- Gap/duplicate detection:

## Known quirks & failure modes

- (e.g., team-name spelling drift, retroactive corrections, missing neutral-venue flags)

## Leakage notes

- Any field whose `knowable_at` is subtle or retroactively revised (flag explicitly).
- Whether this source may be used as a *feature* and at what prediction horizon (market data especially).
