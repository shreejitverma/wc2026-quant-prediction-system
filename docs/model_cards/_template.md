# Model Card: <ID> <name> v<version>

- Status: research | shadow | challenger | champion | retired
- Date:
- Code: `src/wc2026/models/<...>.py`
- Git commit of last fit:

## Purpose & lineage

What it models, and the literature it descends from.

## Data window & features

- Training window / decay half-life:
- Feature families consumed (via `get_features(..., as_of_ts)` only):
- Match-importance / neutral-venue / quasi-home handling:

## Assumptions

- (e.g., conditional independence of goals given rates; stationarity within window)

## What it can capture / cannot capture

- Captures:
- Cannot capture:

## Known biases

- (e.g., favourite-longshot, over-shrinkage of new-generation squads)

## Distrust list

Situations where this model's output should be down-weighted or ignored:
- (dead rubbers, eliminated teams, extreme heat/altitude, thin-data opponents, post-red-card states)

## Evaluation history

| Date | Data | log loss | Brier | RPS | CRPS | vs sharp (CLV) | Notes |
|------|------|----------|-------|-----|------|----------------|-------|
| | | | | | | | |

## Uncertainty output

How this model reports posterior/predictive uncertainty into the Phase 3 uncertainty layer.
