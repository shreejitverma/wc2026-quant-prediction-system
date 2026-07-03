# ADR-0011: Terminal UI stack — FastAPI + Next.js/TypeScript client of the harness

- Status: accepted
- Date: 2026-07-02

## Context

The operator needs a terminal UI for five jobs: understand predictions, see market-making opportunity, inspect fair value, judge the system against the live market, and operate the system.
The repo already contains (a) a FastAPI stub (`wc2026.api`) that served unlabeled mock data, and (b) a Next.js 16 / React 19 / TypeScript frontend scaffold with TanStack Query, Zustand, Tailwind 4, and shadcn-style components.
The maintainer is solo, works evenings/weekends, and the tournament is live now: time-to-first-honest-screen beats completeness.
Frontend is the maintainer's weakest area; the stack must fail loudly and be reasoned about locally.
The UI is a client of the honesty harness, never a bypass: it never writes to the ledger and every future action flows through backend commands that enforce the same fences.

## Decision

We will build a FastAPI + React/TypeScript terminal ("Track B"), hardening the existing scaffold rather than starting greenfield:

- **Backend**: FastAPI over the same JSONL/Parquet/DuckDB artifacts the CLI writes; localhost-only (`127.0.0.1`), explicit CORS origins; exchange credentials never enter the frontend.
- **Frontend**: keep Next.js 16, run purely as a client-side app — no server components fetching data, no Next API routes; FastAPI is the single backend.
- **Server state**: TanStack Query only. Anything the backend could ever disagree with (prices, positions, fair values, runs) is a Query-cached server fact, keyed by endpoint.
- **Client state**: Zustand only for state that is harmlessly lost on refresh (selection, layout, palette). The scaffold's client-side trade blotter is deleted: a trade record living in browser state is a second source of truth that can disagree with the ledger.
- **API contract**: OpenAPI-generated TypeScript types (`make openapi` + `npm run gen:api`); hand-written untyped `fetch` wrappers are replaced, so backend schema drift becomes a compile error.
- **Live data**: one multiplexed WebSocket with topic subscribe/unsubscribe (Phase 1), replacing per-ticker sockets, so there is exactly one reconnect path to get right.

## Alternatives rejected

- **Track A: Streamlit/Panel dashboard** — days to first screen, but its rerun-the-script model fights persistent order-book views, keyboard-first operation, and typed-confirmation controls.
  The maintenance burden that kills solo projects is fighting abstractions, not line count.
- **Vite migration** — greenfield we would choose Vite (no SSR needed for a localhost terminal), but rewriting a working scaffold during a live tournament produces zero decision-making value.
  Clean upgrade point: migrate if Next's build layer ever costs a real evening.
- **Next.js server components / API routes as the backend** — would split backend logic across two languages and two processes, and put harness access behind Node instead of the Python modules that enforce the fences.

## Consequences

Easier: typed end-to-end contract, honest mock mode, one backend to reason about, UI work never blocks on live pipelines.
Harder: the API layer is real backend work before each new screen (every screen needs its endpoint wired to real artifacts first).
Failure mode protected against: a UI that silently renders fabricated or stale numbers — every payload carries provenance (ADR-0012) and unlabeled mock data cannot reach the screen.
