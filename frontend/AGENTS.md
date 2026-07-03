# Frontend agent rules

Vite + React 19 + TypeScript strict SPA — Next.js was removed in ADR-0015; do not reintroduce Next APIs, `"use client"` directives, or `app/`-router conventions.

- Routing is react-router (`src/App.tsx` route table mirrors `NAV_ITEMS` in `Sidebar.tsx`; change both together).
- `src/lib/api.types.ts` is generated (`npm run gen:api`); never hand-edit it.
- Fetchers return the full `Envelope {data, provenance}`; components must consume provenance. `source: "mock"` renders a loud banner and is unactionable.
- Server state lives in TanStack Query only; Zustand only holds state that is harmless to lose on refresh.
- One WebSocket (`src/lib/ws.ts`, ADR-0014); never open another.
- Verify with `npm run lint && npm test && npm run build` before claiming done.
