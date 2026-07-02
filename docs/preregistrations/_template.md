# Pre-registration: PR-NNNN <title>

- Status: draft | frozen | run | concluded
- Author:
- Date frozen (must precede any result):
- Git commit at freeze:

## Hypothesis

The specific, falsifiable claim (e.g., "M4 lineup-conditional beats M1 on CRPS for group-stage totals, out of sample").

## Metric

The single primary metric (proper scoring rule), plus any secondary metrics.
State why hit-rate is *not* used.

## Decision rule & threshold

- Threshold for "success" (numeric, decided now):
- Statistical test (e.g., Diebold-Mariano; bootstrap CI that must exclude zero):
- What outcome would *reject* the hypothesis:

## Sample size / power

- Required N and the power calculation justifying it:
- Data window (train/test split, walk-forward scheme, no contamination):

## Leakage checklist (must be green before running)

- [ ] All features via `get_features(match_id, as_of_ts)` only.
- [ ] No closing-odds-to-predict-pre-close.
- [ ] Test window strictly after train window (time-based CV).
- [ ] Settlement/event definitions match between model and any contract used.

## Result (filled in AFTER running, never before)

- Observed metric:
- Test statistic / CI:
- Conclusion (accept/reject), and what changes as a consequence:
