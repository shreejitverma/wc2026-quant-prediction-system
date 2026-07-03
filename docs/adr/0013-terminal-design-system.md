# ADR-0013: Terminal design system — three reserved color jobs, uncertainty is never a hue

- Status: accepted
- Date: 2026-07-02

## Context

The terminal renders probabilities, edges, staleness, and (later) multi-model comparisons on a dark surface (`#0a0a0a`, dark theme hardcoded).
Color is the fastest channel to the operator's eye and therefore the easiest place for the UI to lie: green/red that implies significance where none exists, uncertainty shaded in a direction hue, status colors reused as series colors.
Palette choices are computable, so they were computed: every set below ran through the dataviz palette validator against the app's actual surface.

## Decision

Three reserved color jobs, never mixed, defined as CSS tokens in `globals.css` and consumed via Tailwind (`text-edge-pos`, `bg-uncertain/35`, …):

- **Edge polarity (diverging)**: blue `#3987e5` = edge in my favor, red `#e66767` = against, neutral gray = no edge.
  Validated pair CVD ΔE 66.4, both ≥3:1 on the surface.
  Deliberately **not** green/red: avoids the deutan red/green trap and the "green = go" reflex; green is reserved for status-good and rarely appears.
- **Uncertainty**: neutral gray `#9ca3af` only, as a translucent band.
  A band must never wear a direction hue — uncertainty visually cannot be misread as favor.
- **Status (reserved, never themed)**: good `#0ca30c`, warning `#fab219` (stale/mock), serious `#ec835a`, critical `#dd5757` (LIVE mode, kill, broken chain).
  Status ships with icon + label, never color alone.
  (Correction 2026-07-02: critical was `#d03b3b`, which met the 3:1 graphical floor but failed WCAG AA 4.5:1 for the small text that wears it — KILL button, LIVE badge, API DOWN — measuring 4.12:1 on the background and 3.73:1 on cards; `#dd5757` keeps the hue and passes both.
  The whole palette contract is now enforced by `src/lib/designTokens.test.ts`: text tokens ≥4.5:1 on both dark surfaces, series tokens ≥3:1, so a palette edit that breaks contrast fails CI.)
- **Series 1–8** for model-comparison charts (Phase 5): the validated dark categorical set, assigned in fixed order, never cycled; CVD floor band (10.3) means direct labels are mandatory, which the chart specs require anyway.

Companion rules baked into the base layer and primitives:

- `font-variant-numeric: tabular-nums` on `body` — digits align in columns everywhere.
- **ProbabilityBar** is the only sanctioned probability rendering; its band prop is required by the type system and enforced again at runtime (a caller without a band gets a visible "NO BAND" refusal, unit-tested).
- **EdgeBadge** precedence (pure function, unit-tested): unconfirmed mapping → quarantined; stale → blanked; market inside band → no edge; below `min_edge` → no edge; only then a signed, glyphed edge in a polarity hue.
- **Time**: UTC transport everywhere; display is local **with the GMT offset spelled out** (`localWithOffset`), plus the UTC clock where both matter. Six venues across four zones make a bare "18:00" a trap.

## Alternatives rejected

- **Green/red for edge polarity** — the trading convention, but it collides with status-good/critical, fails CVD sooner, and trains a "green means act" reflex the stay-flat threshold exists to suppress.
- **Uncertainty as error bars in the point's own color** — indistinguishable from the mark at glance distance; a neutral band read against the market tick is decidable in one look.
- **Per-component ad-hoc colors** — what the scaffold had; it produced a hardcoded green "LIVE" badge in a paper-mode terminal, the exact failure this ADR exists to prevent.

## Consequences

Easier: every later screen composes ProbabilityBar/EdgeBadge/FreshnessDot and inherits the honesty rules without re-deciding them.
Harder: contributors cannot use raw Tailwind color classes for data; anything numeric must go through the primitives.
Failure mode protected against: a colorful screen that overstates certainty — the palette physically lacks a way to say "significant" without the thresholds agreeing.
