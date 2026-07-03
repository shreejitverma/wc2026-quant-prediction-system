# ADR-0008: Scope = Paper-Then-Small-Live, With a Hard Kill-Switch in v1

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Shreejit Verma

---

## Context

**The goal is to earn the right to risk real money.**

This is not a system designed to start live immediately. Even if the model quality is world-class, trading live before the system has been validated on paper trading is irrational risk-taking. The validation requirements are:
1. The model produces positive Closing Line Value (CLV) on paper bets — evidence of genuine pre-closing edge.
2. The risk controls (kill switches, reconciliation, staleness checks) are battle-tested.
3. Drawdown behavior during a cold streak is within pre-registered expectations.

**Bankroll constraint**: Starting capital is small (~$5,000 placeholder; confirmed before live promotion). This means position sizing must be disciplined — a single bad trade should not meaningfully impact the ability to continue operating.

**The kill-switch is not optional**: The single highest-variance risk in prediction market trading is quoting on stale data. If a goal is scored and our data feed is 30 seconds behind, our quotes become stale and sharp traders will immediately pick them off. The kill-switch — which pulls all live quotes within milliseconds of detecting a significant odds shift — is the primary loss-prevention mechanism.

---

## Decision

### Mode Defaults

- **Default mode**: `paper`. Live trading is unreachable until Phase 6/7 pre-registered promotion gates pass.
- **Live mode**: Activated only after ALL of the following are satisfied:
  - Minimum paper sample: ≥200 paper bets.
  - CLV positivity: $\overline{CLV} > 0$ over the paper sample (pre-registered, see PR-LIVE-0001).
  - Calibration bounds: Brier Score and Log-Loss within pre-registered targets.
  - Drawdown behavior: Maximum drawdown within pre-registered simulation expectations.
  - Kill switch: Tested and confirmed functional before first live order.
- **Live scaling**: Starts at minimum position size (10% of Kelly-optimal), scaling up only with continued positive CLV evidence.

### Kill-Switch Configuration

The kill-switch is a v1 deliverable, not a future enhancement. It is configured in `KillSwitchConfig`:

```python
class KillSwitchConfig(BaseModel):
    # Pull all quotes if any data feed is stale for longer than this
    max_data_staleness_seconds: int = 120

    # Hard daily P&L stop in USD — halts trading for the day
    pnl_stop_usd: float = -250.0

    # Reconcile positions against exchange state every cycle
    reconcile_every_cycle: bool = True

    # Offshore odds shift threshold that triggers defensive quote pull
    anomaly_shift_cents: float = 0.08
```

**What each parameter defends against:**

| Parameter | Threat it defends against | Consequence if breached |
|-----------|--------------------------|------------------------|
| `max_data_staleness_seconds` | Quoting on dead data after feed disconnect | Pull all quotes; halt until feed restored |
| `pnl_stop_usd` | Runaway loss from a systematic model error | Halt trading for the day; human review required |
| `reconcile_every_cycle` | Position state mismatch (filled order not recorded) | Alert + halt on reconciliation break |
| `anomaly_shift_cents` | Goal scored/red card before our model updates | Pull all quotes within milliseconds |

### Kelly Fraction

Position sizing uses **Fractional Kelly** with a default fraction of 0.25:

$$
\text{Bet Size} = \frac{\text{Kelly Fraction} \times \text{Edge}}{\text{Odds}}
$$

Full Kelly (fraction = 1.0) is theoretically optimal but requires a perfect model. In practice, our edge estimates have significant estimation error — full Kelly on a miscalibrated model leads to catastrophic drawdowns. Fractional Kelly at 0.25 reduces position sizes by 4×, dramatically improving robustness to model error. The cost is ~75% of the theoretically optimal growth rate.

---

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| **Live from the start** | No earned evidence of edge. Violates pre-registration discipline. High probability of early ruin from model calibration errors before the system is tuned. |
| **Kill switches as a "Phase 7" feature** | The worst-case scenario — being the stale quote a sharp picks off after a goal — is a *Phase 1* risk, not a Phase 7 risk. If the kill switch isn't built before the first live order, it will never be built, and the system will eventually blow up on a data feed disconnect. |
| **Full Kelly sizing** | Estimation error in edge calculations is too large for full Kelly to be appropriate. Even a 10% overestimate of edge leads to catastrophic drawdown probabilities with full Kelly. |

---

## Consequences

### Positive
- The path to real money is **gated by evidence** — no edge, no live trading.
- The loss-prevention machinery (kill switches, reconciliation, P&L stops) exists before the first live order is placed.
- Risk is explicitly bounded: a data feed outage or model version mismatch cannot silently bleed the bankroll.

### Open Items
- Confirm exact bankroll magnitude before live promotion.
- Set per-event and per-portfolio position limits in config.
- Define exact paper sample size required for statistical significance (see PR-LIVE-0001).
