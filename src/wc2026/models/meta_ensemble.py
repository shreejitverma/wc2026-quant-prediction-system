"""Meta-Model Ensembler."""

from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from wc2026.models.base import Model, ScoreDist


class MetaModel(Model):
    """
    Ensembles multiple models using Log-Opinion Pooling or Linear Pooling.
    Weights are dynamically optimized via Log-Loss minimization on a hold-out set.
    """
    def __init__(self, models: list[Model], pool_type: str = 'log', holdout_frac: float = 0.15):
        self.models = models
        self.weights = [1.0 / len(models)] * len(models)
        self.pool_type = pool_type
        self.holdout_frac = holdout_frac

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        if len(df) < 50:
            for model in self.models:
                model.fit(df, as_of_ts)
            self.weights = [1.0 / len(self.models)] * len(self.models)
            return

        df = df.sort_values('date').reset_index(drop=True)
        split_idx = int(len(df) * (1.0 - self.holdout_frac))
        train_df = df.iloc[:split_idx].copy()
        holdout_df = df.iloc[split_idx:].copy()

        for model in self.models:
            model.fit(train_df, as_of_ts)

        model_preds = [] 
        y_true_list = []
        
        for _, match in holdout_df.iterrows():
            hg, ag = match['home_score'], match['away_score']
            y_true = np.array([[1, 0, 0]]) if hg > ag else (np.array([[0, 1, 0]]) if hg == ag else np.array([[0, 0, 1]]))
            y_true_list.append(y_true)

        for model in self.models:
            preds = []
            for _, match in holdout_df.iterrows():
                features = {
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'neutral': match['neutral'],
                    'elo_home': match.get('elo_home', 1300.0),
                    'elo_away': match.get('elo_away', 1300.0)
                }
                match_id = f"{match['home_team']}_vs_{match['away_team']}"
                
                try:
                    dist = model.predict_match(match_id, match['date'], features)
                    preds.append(np.array([[dist.p_home_win(), dist.p_draw(), dist.p_away_win()]]))
                except Exception:
                    preds.append(np.array([[1/3, 1/3, 1/3]]))
            model_preds.append(preds)
            
        def objective(w):
            w_norm = np.exp(w) / np.sum(np.exp(w))
            total_ll = 0.0
            for i in range(len(y_true_list)):
                blended_probs = np.zeros((1, 3))
                for m_idx in range(len(self.models)):
                    blended_probs += w_norm[m_idx] * model_preds[m_idx][i]
                # Fast Manual Cross-Entropy
                total_ll -= float(np.sum(y_true_list[i] * np.log(np.clip(blended_probs, 1e-15, 1.0))))
            return total_ll

        w0 = np.zeros(len(self.models))
        res = minimize(objective, w0, method='BFGS')
        optimized_w = np.exp(res.x) / np.sum(np.exp(res.x))
        self.weights = list(optimized_w)
        
        for model in self.models:
            model.fit(df, as_of_ts)

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        dists = [m.predict_match(match_id, as_of_ts, features) for m in self.models]
        
        max_shape = max(d.probs.shape[0] for d in dists)
        
        padded_matrices = []
        for d in dists:
            mat = d.probs
            pad_h = max_shape - mat.shape[0]
            pad_w = max_shape - mat.shape[1]
            padded = np.pad(mat, ((0, pad_h), (0, pad_w)), mode='constant')
            padded_matrices.append(padded)
            
        if self.pool_type == 'log':
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
            
        return ScoreDist(probs=blended)

    def model_card(self) -> dict:
        return {
            "name": "MetaModel",
            "type": "Ensemble",
            "pool_type": self.pool_type,
            "weights": [float(w) for w in self.weights],
            "sub_models": [m.model_card() for m in self.models]
        }
