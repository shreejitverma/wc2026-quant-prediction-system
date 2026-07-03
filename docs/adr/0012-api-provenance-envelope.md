# ADR-0012: Every API response is a provenance envelope

- Status: accepted
- Date: 2026-07-02

## Context

The UI must never lie: no probability without knowing how fresh it is and which run produced it.
The repo's harness already records provenance on the write side (hash-chained ledger, run records with git/config/data hashes, PIT gate).
The previous API stub served random mock data with nothing marking it as fake — the exact failure the harness exists to prevent, reintroduced at the display layer.
Several pipeline stages are still skeletons, so some endpoints must serve placeholder data for UI development without blocking on live pipelines.

## Decision

Every `/api/v1` response body is `Envelope[T] = {data, provenance}` where provenance carries:

- `source`: `"real"` (read from pipeline artifacts) or `"mock"` (generated placeholder) — load-bearing, not informational;
- `generated_at`: UTC ISO time the response was assembled;
- `data_as_of`: UTC ISO time of the newest underlying datum (`null` = no data yet);
- `run_id` (when applicable), `git_commit` of the serving code, `config_hash` of the active config.

Client rules enforced by convention now and by component tests from Phase 1:

- fetchers return the full envelope, never bare data;
- any screen rendering a `source="mock"` payload shows a loud MOCK banner and its numbers are unactionable;
- "as of" displays come from `data_as_of`/`generated_at`, never from the client clock;
- empty is a definitive answer (`0 entries`, `data_status="empty"`), never an error or a blank.

Endpoints are versioned under `/api/v1`; breaking schema changes require a new version, and the generated TypeScript types turn unhandled drift into compile errors.

## Alternatives rejected

- **Provenance as optional response headers** — headers are invisible to the person reading the screen and get dropped by every intermediate layer; the envelope travels with the data into the Query cache.
- **A global "mock mode" flag for the whole app** — too coarse: real ledger data and mock opportunities legitimately coexist during development, and a single flag would either overclaim or underclaim.
- **No mock endpoints at all** — would block all UI work on pipeline completion, which the build sequence cannot afford mid-tournament.

## Consequences

Easier: the UI can always answer "how fresh, from which run, real or not" for any number on screen; staleness/quarantine rendering becomes a mechanical consequence of the payload.
Harder: every new endpoint must decide and declare its provenance; responses are slightly larger.
Failure mode protected against: trading on mock, stale, or unattributable numbers during a live match window.
