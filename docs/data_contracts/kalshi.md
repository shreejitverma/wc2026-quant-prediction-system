# Data Contract: Kalshi Markets & Orderbooks

- Tier: 3
- Access: free (public API, no auth for market data and orderbooks)
- Base URL: https://api.elections.kalshi.com/trade-api/v2
- robots.txt / ToS: Kalshi public API; free to read, no auth required for market data
- Rate limit & backoff policy: polite 2-second minimum between requests; exponential backoff on 429/5xx
- Idempotency key (market list): `{date}/markets_{series}.json`
- Idempotency key (orderbook): `{date}/book_{ticker}_{HHMMSS}.json` (always fresh)

## Key endpoints

| Endpoint | Auth | Returns |
|----------|------|---------|
| `GET /markets?series_ticker=X&limit=N` | None | Paginated market list (sparse fields) |
| `GET /markets/{ticker}` | None | Full market record incl. `rules_primary` |
| `GET /markets/{ticker}/orderbook` | None | L2 book: `orderbook_fp.{yes_dollars, no_dollars}` |
| `GET /markets/{ticker}/trades` | Required | Trade tape (not in scope: ADR-0007) |

## Schema: market record

| Field | Type | `knowable_at` | Notes |
|-------|------|---------------|-------|
| ticker | str | Fetch time | e.g. `KXWCADVANCE-26JUL05MEXENG-MEX` |
| event_ticker | str | Fetch time | Parent event |
| status | str | Fetch time | `active`, `closed`, `settled` |
| title | str | Fetch time | Human-readable name |
| yes_ask_dollars | float | Fetch time | YES ask price in USD (0-1) |
| yes_bid_dollars | float | Fetch time | YES bid price in USD (0-1) |
| no_ask_dollars | float | Fetch time | NO ask price in USD (0-1) |
| no_bid_dollars | float | Fetch time | NO bid price in USD (0-1) |
| last_price_dollars | float | Fetch time | Last traded price |
| volume_fp | float | Fetch time | Total volume in USD |
| volume_24h_fp | float | Fetch time | 24h volume in USD |
| open_interest_fp | float | Fetch time | Open interest in USD |
| rules_primary | str | Fetch time | **Settlement text - MUST be parsed before pricing** |
| close_time | ISO str | Fetch time | When market closes for trading |
| expected_expiration_time | ISO str | Fetch time | Expected settlement time |

## Schema: orderbook

| Field | Notes |
|-------|-------|
| `orderbook_fp.yes_dollars` | List of [price_str, cumulative_size_str] for YES bids |
| `orderbook_fp.no_dollars` | List of [price_str, cumulative_size_str] for NO bids |
| Prices | USD (0.0100 = 1 cent = 0.01 probability) |
| Sizes | USD cumulative at that price level |

## WC2026 series tracked

`KXWCADVANCE`, `KXWCGOAL`, `KXWCTOTAL`, `KXWCCORNERS`, `KXWCSHOT`, `KXSOCCERBTTS`, `KXWCGROUPBOTTOM`, `KXWCREGIONKO`, `KXWCGOALRECORD`, `KXWCGOALLEADER`, `KXWCLONGESTPEN`, `KXWCMENTION`, `KXWCSONG`, `KXWC2HSPREAD`, `KXWCSAVE`

## Settlement risk and contract mapping

- **`rules_primary` is the ground truth for settlement.** Never infer what "advances" or "wins" means from the market title alone; read the exact rule text.
- Confirmed example (2026-07-01): `KXWCADVANCE-26JUL05MEXENG-MEX.rules_primary` = "If Mexico advance past England in the Mexico vs England soccer match in the Round Of 16 of the FIFA World Cup, then the market resolves to Yes."
- **"advances" vs "wins in 90"**: Round-of-16 Kalshi ADVANCE markets resolve on the team that progresses, including via extra time and penalties. This differs from 90-minute match outcome.
- Settlement timer: 45 seconds post-event (fast, low UMA-like risk vs Polymarket).
- Postponement/void rules: check `early_close_condition` field.

## Leakage notes

- Bid/ask prices at fetch time are market prices, not model-derived. They are admissible as features only for prediction horizons where the market price was observable before the fact being predicted (i.e., don't use a price snapshot taken after an event to predict that event).
- For CLV measurement: the *closing* price is the benchmark; use the latest pre-close snapshot, not an intra-day snapshot.
- `volume_fp` and `open_interest_fp` are cumulative; do not use as a proxy for "current" activity without differencing over time.
