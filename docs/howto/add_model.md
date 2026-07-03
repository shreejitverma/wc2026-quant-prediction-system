# How-To: Add a Model to the Suite

This guide walks through the steps required to add a new prediction model to the system, register it in the Meta-Ensembler, and verify its out-of-sample performance.

---

## Step 1: Inherit from the `Model` Base Class

Every predictive model must inherit from the abstract base class `Model` defined in [`src/wc2026/models/base.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/models/base.py).

Create a new file `src/wc2026/models/new_model.py`:

```python
from datetime import datetime
import numpy as np
import pandas as pd
from wc2026.models.base import Model, ScoreDist


class NewModel(Model):
    """
    Detailed explanation of your model assumptions.
    """
    def __init__(self, hyperparameter_val: float = 0.5):
        self.hyperparameter = hyperparameter_val
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        """
        Fits the model strictly on matches played before as_of_ts.
        """
        # Fit logic
        self.is_fitted = True

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        """
        Returns a 15x15 joint probability matrix.
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction.")
            
        # Prediction logic
        # Probs shape must be (15, 15), summing to 1.0
        probs = np.zeros((15, 15))
        probs[0, 0] = 1.0  # mock prediction
        return ScoreDist(probs=probs)

    def model_card(self) -> dict:
        """
        Returns model metadata for tracking.
        """
        return {
            "name": "NewModel",
            "type": "CustomType",
            "hyperparameter": self.hyperparameter,
            "fitted": self.is_fitted
        }
```

---

## Step 2: Write Unit Tests

Add a new unit test class inside `tests/features/` or `tests/models/`:

```python
import pytest
from datetime import datetime
import pandas as pd
from wc2026.models.new_model import NewModel


def test_new_model_prediction():
    model = NewModel()
    # Mock data
    df = pd.DataFrame([{
        "date": datetime(2026, 6, 1),
        "home_team": "BRA",
        "away_team": "ARG",
        "home_score": 1,
        "away_score": 0,
        "neutral": True
    }])
    model.fit(df, datetime(2026, 6, 2))
    
    features = {"home_team": "BRA", "away_team": "ARG", "neutral": True}
    dist = model.predict_match("match_1", datetime(2026, 6, 2), features)
    
    assert dist.probs.shape == (15, 15)
    assert dist.probs.sum() == pytest.approx(1.0)
```

---

## Step 3: Register in the Meta-Ensembler

Open `src/wc2026/ops/cron.py` or your local instantiation script and add the model instance to the ensembler parameters:

```python
from wc2026.models.new_model import NewModel
from wc2026.models.meta_ensemble import MetaModel

# Instantiate individual models
m1 = DixonColesModel()
m_new = NewModel()

# Register in ensembler
ensemble = MetaModel(models=[m1, m_new], pool_type="log")
```

---

## Step 4: Run a Verification Check

1. Add your model card summary to [`docs/model_cards/README.md`](file:///Users/shreejitverma/github/footbal_prediction/docs/model_cards/README.md).
2. Execute the verification suite:
   ```bash
   make verify
   ```
3. Run walk-forward backtests to evaluate if the new model improves the ensemble's Brier Score and Log Loss.
