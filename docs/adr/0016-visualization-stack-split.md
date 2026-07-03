# ADR-0016: Visualization stack — custom DOM/SVG for bespoke charts, recharts for standard time series

- Status: accepted
- Date: 2026-07-02

## Context

The terminal needs two very different kinds of chart.
Bespoke, high-density, honesty-critical pieces: the scoreline heatmap, the fair-value waterfall, order-book depth ladders (Phase 4), probability bars.
Standard time series: price vs fair value, CLV curves, calibration plots (Phase 5).
The maintainer is solo; every chart is maintained by the person it might mislead.

## Decision

Split by whether the chart's honesty rules fit a library's data model:

- **Custom DOM/SVG** (plain React, styled with the ADR-0013 tokens) for bespoke pieces: `ScorelineHeatmap`, `FairValueWaterfall`, `ProbabilityBar`, and the Phase 4 depth ladder.
  These components own hard honesty rules - alpha strictly proportional to probability, refusal to render inconsistent decompositions, disclosed truncation - which are one `if` statement in our own component and a fight against defaults in any library.
  They are also small (a heatmap is a CSS grid; a waterfall is four positioned divs), so "custom" costs less than a library's configuration surface.
- **recharts** for standard time series (`FairValueTimeline` now; CLV/calibration later): axes, tooltips, responsive containers, and reference lines are genuinely hard to rebuild well, and the time-series honesty rules (fixed 0-1 domains, neutral band areas, labeled event markers) map cleanly onto recharts props.
- Either way, ink colors come only from the ADR-0013 CSS tokens (`var(--series-1)`, `var(--uncertain)`); a hardcoded hex in a chart is a review-blocking defect.

## Alternatives rejected

- **One library for everything (recharts/visx/d3)** — the heatmap and waterfall would spend their complexity budget bending a library's data model instead of enforcing honesty rules; visx/d3 are more flexible but bring a much larger API for a solo maintainer to hold.
- **Everything hand-rolled** — rebuilding time axes, tick placement, and tooltip positioning is real work with no honesty payoff; recharts does it acceptably and is already a dependency.
- **Canvas/WebGL for performance** — nothing on this terminal exceeds a few hundred SVG nodes per chart; if the Phase 4 book view ever does, revisit for that component only.

## Consequences

Easier: honesty rules live as plain code and unit tests (`ScorelineHeatmap.test.tsx`, `FairValueWaterfall.test.tsx`); charting-library upgrades touch only standard time series.
Harder: two idioms coexist; contributors must pick the right side (rule of thumb: if the chart has a refusal state, it is custom).
Failure mode protected against: a library default (auto-scaled y-axis, minimum bar heights, interpolated gaps) silently reintroducing a lie that ADR-0013 forbids.
