# ADR-0008: Scope = paper-then-small-live, with a hard kill-switch/reconciliation layer in v1

- Status: accepted
- Date: 2026-07-01

## Context

Operator constraint (2026-07-01): goal is paper-first, then small live after gates pass; the kill-switch and reconciliation layer is a hard v1 requirement, not a later add-on.
Bankroll is small (default assumption: order of a few thousand USD; `risk.bankroll_usd = 5000` placeholder until the operator confirms — override in config).

## Decision

We will:
- Default `mode = paper`. Live is unreachable until Phase 6/7 pre-registered promotion gates pass (minimum paper sample, CLV positivity, calibration bounds, drawdown behavior), and live starts at minimum size.
- Treat the kill-switch/reconciliation layer as a v1 deliverable with real teeth, configured in `KillSwitchConfig`:
  - `max_data_staleness_seconds` — pull all quotes if any feed is stale (defends against quoting on dead data).
  - `pnl_stop_usd` — hard daily P&L stop.
  - `reconcile_every_cycle` — positions reconciled against exchange state every cycle; a reconciliation break halts trading.
- Size with fractional Kelly (`kelly_fraction = 0.25` default), justified from estimation-error math in Phase 6/7, never full Kelly.

## Alternatives rejected

- **Live from the start** — no earned evidence of edge; violates the pre-registration discipline.
- **Kill switches "later"** — the one place where engineering rigor genuinely pays in this market is not being the stale quote a sharp picks off after a goal/red card; deferring it defeats the purpose.

## Consequences

The path to real money is gated by evidence, and the loss-prevention machinery exists before the first live order.
This is the correct place for the operator's low-latency/systems instincts to be spent: recording fidelity, kill switches, reconciliation — not quote speed.
Failure mode avoided: a data-feed outage or model-version mismatch quietly bleeding the bankroll.

## Open item

Confirm bankroll magnitude and per-event/portfolio limits; current values are placeholders.
