# ADR-0015: Migrate the frontend build layer from Next.js to Vite

- Status: accepted
- Date: 2026-07-02
- Amends: ADR-0011 (supersedes its "Vite migration rejected" alternative; every other decision in 0011 stands)

## Context

ADR-0011 kept the Next.js 16 scaffold to avoid a mid-tournament rewrite, while noting that greenfield we would choose Vite: the terminal is a localhost SPA with a single FastAPI backend, so SSR, server components, and Next API routes are pure overhead.
The operator reviewed that trade-off and vetoed it: one build tool with one mental model is worth the migration cost now, before more screens accrete on top of the Next conventions.
An audit during migration found the coupling was thin (three files imported Next APIs) and found a latent defect: the `next/font` CSS variables were never applied to `<body>`, so the terminal had been rendering in browser-default fonts the whole time.

## Decision

- **Vite 8 + `@vitejs/plugin-react-swc`** (SWC, not Babel: `@vitejs/plugin-react@6` drags a Babel 8 RC peer-dependency chain; the SWC plugin has no Babel at all).
- **react-router 8** in plain library mode; the route table in `src/App.tsx` mirrors `NAV_ITEMS` in `Sidebar.tsx` and the two change together.
- **One config file** (`vite.config.mts`) serves dev, build, and vitest; the separate `vitest.config.mts` is deleted.
- **Fonts bundled locally** via `@fontsource-variable/geist(-mono)` — no network font fetch at build or run time (local-first), and the broken font wiring is fixed by defining real `--font-sans`/`--font-mono` stacks in `globals.css`.
- **Env**: `NEXT_PUBLIC_API_URL` becomes `VITE_API_URL` (`import.meta.env`, typed in `src/vite-env.d.ts`).
- **Lint**: `eslint-config-next` replaced by typescript-eslint + `eslint-plugin-react-hooks` flat configs on eslint 10; generated `api.types.ts` is lint-ignored.
- **Stricter compiler**: `noUnusedLocals`/`noUnusedParameters` on; the dead code they exposed was removed rather than suppressed.
- React Compiler (`babel-plugin-react-compiler`) is dropped: it is a performance optimization requiring a Babel pass; reintroduce deliberately if profiling ever justifies it.

## Alternatives rejected

- **Stay on Next.js** (ADR-0011's original call) — defensible, but the operator owns the maintenance budget and chose the simpler toolchain while the surface is still small; the migration cost was one evening, paid once.
- **`@vitejs/plugin-react` (Babel)** — peer-dependency conflict with Babel 8 RC packages; SWC plugin avoids the entire Babel dependency tree.
- **TanStack Router** — typed routes are attractive, but nine static routes do not justify a second router mental model next to TanStack Query; revisit if route params proliferate (match/contract detail pages may reopen this).

## Consequences

Easier: one build tool, one config, faster builds (~260 ms production build), no framework conventions to hold in mind, fonts actually load.
Harder: no file-based routing — new screens must be registered in both `App.tsx` and `NAV_ITEMS` (deliberate: the pair is the navigation contract).
CI is unchanged: `npm run lint` and `npm run build` keep their names.
Verification at migration time: `tsc --noEmit` clean, 13/13 vitest, eslint clean, production build succeeds.
