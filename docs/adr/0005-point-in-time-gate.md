# ADR-0005: Single point-in-time access gate, enforced by property tests

- Status: accepted
- Date: 2026-07-01

## Context

Look-ahead bias is the dominant error term in sports prediction, not a minor one.
Football outcomes are low-scoring Poisson noise with a genuinely low predictability ceiling, so the apparent skill injected by even a small leak (a market value scraped "today" joined onto last month's match; a suspension flag reflecting the card shown *in* the match being predicted; closing odds used to "predict" a pre-close price) can dwarf the real signal.
Discipline does not survive month three of a solo build.
Leak-prevention must be mechanical.

## Decision

We will expose exactly one read path for features: `as_of(ts)` (Phase 0 primitive `wc2026.pit.PointInTimeStore`; Phase 2 feature store is a persistent, typed specialization of the same contract).
It can only ever return facts whose `knowable_at <= ts`.
The invariant is enforced by property-based tests (`tests/test_pit.py`, Hypothesis) asserting that no future fact ever leaks and no admissible fact is ever dropped.
Those tests are wired into pre-commit, so a change that breaks the invariant cannot be committed.

## Alternatives rejected

- **"Be careful in feature code"** — promises, not proof; the first thing to fail under deadline pressure.
- **Timestamp columns without an enforced gate** — the gate is the point; a column you can forget to filter on is not protection.
- **A feature-store product (Feast/Tecton)** — heavy infrastructure that still does not give the property-test leak proof, which is the thing that actually matters.

## Consequences

Look-ahead becomes impossible to construct through the sanctioned path, not merely discouraged.
Every model and every backtest shares one leak-proof gate.
Cost: features must carry an honest `knowable_at`, which forces careful thinking about when each datum was actually observable (a feature, not a bug).
Failure mode avoided: a beautiful backtest and a losing live book.
