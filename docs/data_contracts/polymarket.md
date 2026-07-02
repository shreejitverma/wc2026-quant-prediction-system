# Data Contract: Polymarket (Gamma API + CLOB)

- Tier: 3
- Access: free read (no auth for public data; US trading geo-restricted per ADR-0007)
- Gamma API: https://gamma-api.polymarket.com
- CLOB API: https://clob.polymarket.com
- robots.txt / ToS: Public API; US persons geo-restricted for trading; read-only CLOB for benchmarking
- Rate limit & backoff policy: polite 2-second minimum; exponential backoff on 429/5xx
- Idempotency key: `{date}/events_search_{keyword}.json`, `{date}/clob_{token_id}_{HHMMSS}.json`

## Key endpoints

| Endpoint | Auth | Returns |
|----------|------|---------|
| `GET gamma/events?q={keyword}&limit=N` | None | Event list with embedded markets |
| `GET gamma/markets?slug={slug}` | None | Single market by slug |
| `GET clob/book?token_id={id}` | None | L2 orderbook for a YES or NO token |

## WC2026 market discovery caveat

Tag-based search (`tag_slug=world-cup-2026`) returns unrelated markets (confirmed probe 2026-07-01). Use keyword search (`q=world+cup`, `q=FIFA`) and maintain a manual slug registry in `configs/polymarket_slugs.yaml` as the stable index. Update it when new WC markets launch.

## Schema: Gamma market

| Field | Type | `knowable_at` | Notes |
|-------|------|---------------|-------|
| conditionId | str | Fetch time | Primary key (hex) |
| questionId | str | Fetch time | |
| question | str | Fetch time | Human-readable question |
| description | str | Fetch time | Resolution rules (must be parsed before pricing) |
| slug | str | Fetch time | URL slug |
| endDate | ISO str | Fetch time | Market expiry |
| liquidity | float | Fetch time | USDC liquidity |
| tokens[0] | str | Fetch time | YES token_id (for CLOB lookups) |
| tokens[1] | str | Fetch time | NO token_id |
| resolutionSource | str | Fetch time | Data source for resolution |

## Schema: CLOB orderbook

| Field | Notes |
|-------|-------|
| `bids[].price` | USDC (0.0-1.0) |
| `bids[].size` | USDC |
| `asks[].price` | USDC |
| `asks[].size` | USDC |

## Settlement risk: UMA oracle

Polymarket uses UMA as its resolution oracle. **This is a priced risk:**
- Disputes can take 1-7 days post-event.
- Historical cases of UMA resolving against the economically obvious outcome exist (DOGE coin market, 2021).
- For WC markets: prefer contracts whose `resolutionSource` says "Official FIFA match records" over "major media consensus."
- Factor settlement risk into fair value (Phase 5): `fair_value = model_prob × (1 - p_resolution_error) - fee`.
- Never treat Polymarket prices as equivalent to Kalshi prices without adjusting for UMA risk.

## Contract mapping obligations (Phase 5)

Before pricing any Polymarket contract:
1. Read `description` field fully.
2. Confirm `resolutionSource`.
3. Classify edge case: does "advances" here mean "wins in 90" or "wins the tie" (incl. extra time/penalties)?
4. Log the classification in `docs/data_contracts/polymarket_mapped_contracts.yaml`.

## Leakage notes

Same as Kalshi: CLOB prices are admissible features only at the prediction horizon where the price was observable before the outcome. Post-close prices are ground truth benchmarks, not features.
