# ADR-0006: Edge thesis — coherence, settlement precision, information timing (not out-leveling the sharp)

- Status: accepted
- Date: 2026-07-01

## Context

The sharpest closing prices (Pinnacle, Betfair) are empirically very hard to beat on the level.
Hvattum & Arntzen (2010) and the broader literature show Elo-family and goal models struggle to add information *over* the closing line.
A solo operator pointing the system at "I can out-predict the market on France to beat Argentina" grinds into the vig against better-resourced participants and loses slowly and confidently.
But the market is assembled by many participants pricing *marginals* independently, so it is frequently internally incoherent across correlated contracts, and retail venues misread settlement edge cases.

## Decision

We will treat the durable edge for a solo operator as three structural sources, in priority order:
1. **Cross-venue + internal-coherence pricing** off the joint simulator (Kalshi vs Polymarket vs de-vigged sharp; "reach final" vs the product along the bracket path; group-winner vs match-level). This is the safest edge class.
2. **Settlement-definition precision** — reading contract text more carefully than the crowd ("advances" ≠ "wins in 90"; UMA/resolution risk priced, not ignored).
3. **Information timing** — expected-XI vs confirmed-XI deltas at lineup release.

Marginal 1X2 vs the de-vigged sharp close is a **benchmark to calibrate against, not a market to beat**, with a "stay flat" default when the only claim is "I think the sharp is wrong on the level."

## Alternatives rejected

- **"Beat the sharp on 1X2" as the thesis** — lowest and possibly negative expected edge, highest competition.
- **Pure cross-venue stat-arb ignoring settlement text** — the classic trap where the "edge" is a definition mismatch and you get sawn off at resolution (edge class c, not d, in the Phase 5 taxonomy).
- **In-play as the primary battlefield** — that is where firms with official low-latency feeds live; the solo strategy there is defensive (quote wide or pull).

## Consequences

The joint simulator and the contract mapper are promoted from plumbing to the primary alpha engine, which reorders model and market-selection investment accordingly.
Failure mode avoided: competing where there is no edge, and mistaking settlement mismatches for genuine inconsistency.
This is a thesis to be *tested*, not assumed: Phase 7 measures realized CLV by edge class, and the thesis is revised if the data disagrees.
