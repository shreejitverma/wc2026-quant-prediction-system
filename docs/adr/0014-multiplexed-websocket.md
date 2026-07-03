# ADR-0014: One multiplexed WebSocket with topic subscriptions

- Status: accepted
- Date: 2026-07-02

## Context

The terminal needs live order books, quote/fill events, alerts, and health pushes.
The scaffold opened one WebSocket **per ticker** (`/ws/orderbook/{ticker}`): an opportunity board with 20 rows means 20 connections, 20 reconnect loops, 20 heartbeats — reconnect handling is the classic WS bug, multiplied.
The solo-maintainer constraint says: build the hard part once.

## Decision

One socket, `WS /api/v1/ws`, with topic subscribe/unsubscribe:

- Client sends `{"subscribe": ["health", "ledger", "book.<ticker>"], "after_seq"?: N}` / `{"unsubscribe": [...]}`.
- Server sends `{"topic", "source": "real"|"mock", "ts_utc", "data"}` — the stream is under the same provenance contract as REST (ADR-0012).
- Topics now: `health` (REAL — byte-identical Envelope to `GET /api/v1/health`, shared builder), `ledger` (REAL — tails new entries past a cursor; `after_seq` backfills, default cursor is the current head), `book.<ticker>` (MOCK until ingestion persists snapshots; deterministic per (ticker, step)).
- Subscribing pushes an immediate snapshot, so consumers render without waiting a tick and tests are deterministic.
- Client side (`lib/ws.ts`): a single `TerminalSocket` with exponential backoff (1s→30s cap, jitter), automatic resubscribe of all topics on reconnect, and a status surfaced to the status strip (`ws ● / … / ○`).
  Pushed server state lands in the TanStack Query cache under the same keys REST fills, so components have one source of truth regardless of transport.

## Alternatives rejected

- **Per-ticker sockets** (scaffold) — N reconnect paths; also breaks the browser's per-host connection budget under load.
- **SSE** — no client→server subscribe/unsubscribe without query-string hacks; the board changes its subscriptions constantly as rows scroll/expand.
- **Polling only** — workable for health (kept as a 30s fallback) but wrong for books during a goal window, exactly when it matters.

## Consequences

Easier: adding a topic (quotes, fills, alerts in Phases 4–6) is a server-side dispatch case plus a `useTopic` call; reconnect correctness is inherited.
Harder: the single socket is a single point of failure — mitigated by REST polling fallbacks on critical queries and the loud `ws ○` indicator.
Failure mode protected against: the silent dead-feed, where a stale board looks calm precisely during the event that killed the connection.
