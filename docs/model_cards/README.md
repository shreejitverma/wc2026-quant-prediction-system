# Model Cards

One card per model *version*, documenting what it assumes, what it can and cannot capture, and its evaluation history.
A model without a card is not allowed into the ensemble.

Populated in Phase 3.
Use `_template.md` for each model version.

## Planned models

| ID | Model | Lineage |
|----|-------|---------|
| M1 | Dixon-Coles / bivariate Poisson | Maher 1982 -> Dixon & Coles 1997 -> Karlis & Ntzoufras 2003 |
| M2 | Dynamic state-space ratings | Rue & Salvesen 2000 |
| M3 | Bayesian hierarchical goals | partial pooling; numpyro/JAX |
| M4 | Player-aggregation team strength | club-form -> national strength; lineup-conditional |
| M5 | Gradient boosting (LightGBM) | ordered-outcome + goal-count heads |
| M6 | Market-implied | de-vig: proportional / power / Shin 1993 |

Every card must state the situations where the model should be *distrusted* (dead rubbers, eliminated teams, extreme-heat kickoffs, thin-data opponents).
