# Model Cards

One card per model *version*, documenting what it assumes, what it can and cannot capture, and its evaluation history.
A model without a card is not allowed into the ensemble.

**All models are fully implemented and integrated in the modeling suite.** 
For a rigorous breakdown of the LaTeX mathematical equations, statistical priors, parameters, and failure modes governing all models, see the **[Mathematical Modeling Suite deep-dive](../models.md)**.

## Implemented Models Catalog

| ID | Model | File | Status |
|----|-------|------|--------|
| M1 | Dixon-Coles Bivariate Poisson | [dixon_coles.py](../../src/wc2026/models/dixon_coles.py) | **built** |
| M2 | Dynamic State-Space ratings | [state_space.py](../../src/wc2026/models/state_space.py) | **built** |
| M3 | Bayesian hierarchical goals | [hierarchical.py](../../src/wc2026/models/hierarchical.py) | **built** |
| M4 | Player-aggregation team strength | [player_agg.py](../../src/wc2026/models/player_agg.py) | **built** (conditional on lineup drop) |
| M5 | Gradient boosting (LightGBM) | [gbm.py](../../src/wc2026/models/gbm.py) | **built** |
| M6 | Market-implied Bivariate Poisson | [market_implied.py](../../src/wc2026/models/market_implied.py) | **built** |

Every model version lists the exact situations where the model should be *distrusted* (dead rubbers, key player suspensions, friendly matches, early red cards, illiquid books). Check `docs/models.md` for the complete operational breakdown of each model's failure modes.
