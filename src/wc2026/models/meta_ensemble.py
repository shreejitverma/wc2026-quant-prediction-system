"""Meta-Model Ensembler."""

from datetime import datetime

import numpy as np

from wc2026.models.base import Model, ScoreDist


class MetaModel(Model):
    """
    Ensembles multiple models using Log-Opinion Pooling or Linear Pooling.
    """
    def __init__(self, models: list[Model], weights: list[float] = None, pool_type: str = 'log'):
        self.models = models
        if weights is None:
            self.weights = [1.0 / len(models)] * len(models)
        else:
            if not np.isclose(sum(weights), 1.0):
                raise ValueError("Weights must sum to 1.0")
            self.weights = weights
        self.pool_type = pool_type

    def fit(self, df, as_of_ts: datetime):
        """
        Fits each sub-model. In a full system, weights are also refit here using out-of-sample data.
        """
        for model in self.models:
            model.fit(df, as_of_ts)

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        dists = [m.predict_match(match_id, as_of_ts, features) for m in self.models]
        
        # We need all dists to have the same shape. Find max_goals.
        max_shape = max(d.prob_matrix.shape[0] for d in dists)
        
        # Pad matrices to max_shape
        padded_matrices = []
        for d in dists:
            mat = d.prob_matrix
            pad_h = max_shape - mat.shape[0]
            pad_w = max_shape - mat.shape[1]
            padded = np.pad(mat, ((0, pad_h), (0, pad_w)), mode='constant')
            padded_matrices.append(padded)
            
        if self.pool_type == 'log':
            # Log-opinion pooling: prod(p_i ^ w_i)
            # Add small epsilon to prevent log(0)
            eps = 1e-12
            log_p = np.zeros((max_shape, max_shape))
            for mat, w in zip(padded_matrices, self.weights, strict=False):
                log_p += w * np.log(np.clip(mat, eps, 1.0))
            
            blended = np.exp(log_p)
            blended /= np.sum(blended)
            
        elif self.pool_type == 'linear':
            blended = np.zeros((max_shape, max_shape))
            for mat, w in zip(padded_matrices, self.weights, strict=False):
                blended += w * mat
            blended /= np.sum(blended)
        else:
            raise ValueError(f"Unknown pool_type: {self.pool_type}")
            
        return ScoreDist(
            home_team=features.get('home_team', 'Unknown'),
            away_team=features.get('away_team', 'Unknown'),
            prob_matrix=blended
        )

    def model_card(self) -> dict:
        return {
            "name": "MetaModel",
            "type": "Ensemble",
            "pool_type": self.pool_type,
            "weights": self.weights,
            "sub_models": [m.model_card() for m in self.models]
        }
