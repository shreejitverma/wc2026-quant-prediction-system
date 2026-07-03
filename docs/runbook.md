# Runbook

Operational reference for the wc2026 system.
Phase 0 covers setup, verification, and the honesty-harness primitives.
Later phases will add ingest, pipeline, and trading operations sections.

## Setup

```bash
# One-time: install uv (https://astral.sh/uv) if not present.
curl -LsSf https://astral.sh/uv/install.sh | sh

make setup      # creates .venv (pinned Python 3.12) and installs from uv.lock
make hooks      # install pre-commit hooks (includes the leakage gate)
```

## Daily / per-change verification

```bash
make verify     # ruff lint + pytest + Phase 0 end-to-end self-check
make test       # pytest only
make selfcheck  # end-to-end smoke of the honesty harness
```

`make verify` is the Phase 0 gate: it must be green before any change lands.

## Terminal UI (API + frontend)

```bash
make bootstrap-data   # one-time: create data/ ledger+runs artifacts (idempotent)
make api              # FastAPI on 127.0.0.1:8000 (docs at /docs)
cd frontend && npm install && npm run dev   # Next.js on localhost:3000
```

After any API schema change, regenerate the typed client:

```bash
make openapi                     # export frontend/openapi.json
cd frontend && npm run gen:api   # regenerate src/lib/api.types.ts
```

Contract (ADR-0011, ADR-0012): every response is `{data, provenance}`; `provenance.source="mock"` renders a loud MOCK banner and those numbers are not actionable.
Real endpoints today: `/api/v1/health`, `/api/v1/ledger[...]`, `/api/v1/runs[...]`.
Mock until the pipeline persists artifacts: `/api/v1/matches`, `/api/v1/opportunities`, `book.*` WS topics.
Live channel: one multiplexed `WS /api/v1/ws` with topic subscriptions (ADR-0014); topics `health` and `ledger` are real.

Frontend unit tests (honesty primitives, time discipline):

```bash
cd frontend && npm test
```

Keyboard: `⌘K` command palette, `⇧⌘K` kill-switch dialog (wired to backend commands in Phase 4).

## Reproducibility contract

- `uv.lock` is committed; `make setup` installs exactly those versions.
- Every run recorded via `wc2026.runs.log_run` captures git commit + config/data/feature hashes.
- To reproduce a historical result: check out its recorded git commit, restore the config with the recorded hash, and re-run — outputs hash-match bit-for-bit.
- The ledger and runs files under `data/` are machine-local and git-ignored; the *code and config* that generate them are versioned.

## Kill switches (Phase 6+; configured now)

Configured in `configs/*.yaml` under `kill_switch`:
- `max_data_staleness_seconds` — pull quotes if any feed is stale.
- `pnl_stop_usd` — hard daily P&L stop.
- `reconcile_every_cycle` — halt on any position/exchange reconciliation break.

## Placeholders (not yet implemented)

- `make daily` — Phase 8 full pipeline.
- `make news-cycle` — Phase 8 event-driven fast path.

## Common issues

- **`uv: command not found`** — add `~/.local/bin` to PATH (uv installs there).
- **Wheel build failures on Python 3.14** — this project pins Python 3.12 via `.python-version`; let uv manage it (`uv python install 3.12`).
- **`git_dirty=None` in a run record** — HEAD is unborn (no commit yet) or not a git repo; make an initial commit to activate provenance.
