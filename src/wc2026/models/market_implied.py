"""M6 - Market-implied model."""

from datetime import datetime
from math import factorial

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from wc2026.models.base import Model, ScoreDist


class MarketImpliedModel(Model):
    """
    Infers the full ScoreDist by fitting a Bivariate Poisson distribution 
    to match market-implied 1X2 probabilities.
    """
    def __init__(self, max_goals: int = 10):
        self.max_goals = max_goals
        # Precompute factorials
        self._facts = np.array([factorial(i) for i in range(self.max_goals + 1)])
        self._goals_range = np.arange(self.max_goals + 1)

    def fit(self, match_results: pd.DataFrame, as_of_ts: datetime):
        """No historical fitting required for pure market-implied model."""
        pass

    def _pois_probs(self, lambda_: float, mu: float, rho: float) -> np.ndarray:
        p_home = (lambda_ ** self._goals_range) * np.exp(-lambda_) / self._facts
        p_away = (mu ** self._goals_range) * np.exp(-mu) / self._facts
        pois_matrix = np.outer(p_home, p_away)

        if rho != 0.0:
            tau = np.ones((self.max_goals + 1, self.max_goals + 1))
            tau[0, 0] = max(1e-10, 1.0 - lambda_ * mu * rho)
            tau[0, 1] = max(1e-10, 1.0 + lambda_ * rho)
            tau[1, 0] = max(1e-10, 1.0 + mu * rho)
            tau[1, 1] = max(1e-10, 1.0 - rho)
            pois_matrix *= tau

        pois_matrix /= pois_matrix.sum()
        return pois_matrix

    def _obj_func(self, params, target_home, target_draw, target_away):
        lambda_, mu = params[0], params[1]
        probs = self._pois_probs(lambda_, mu, 0.0)
        
        p_home = np.tril(probs, -1).sum()
        p_draw = np.trace(probs)
        p_away = np.triu(probs, 1).sum()
        
        # Mean squared error
        return (p_home - target_home)**2 + (p_draw - target_draw)**2 + (p_away - target_away)**2

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        """
        features must contain devigged probabilities:
        - market_p_home: float
        - market_p_draw: float
        - market_p_away: float
        """
        target_home = features.get('market_p_home')
        target_draw = features.get('market_p_draw')
        target_away = features.get('market_p_away')
        
        if target_home is None or target_draw is None or target_away is None:
            raise ValueError(f"MarketImpliedModel requires market_p_home, market_p_draw, market_p_away in features for match {match_id}")

        # Normalize just in case
        total = target_home + target_draw + target_away
        target_home /= total
        target_draw /= total
        target_away /= total

        # Solve for lambda and mu (fixing rho=0 for simplicity if O/U is absent)
        # Init guess: roughly 1.5 goals each
        res = minimize(
            self._obj_func,
            x0=[1.5, 1.5],
            args=(target_home, target_draw, target_away),
            method='L-BFGS-B',
            bounds=[(0.01, 8.0), (0.01, 8.0)]
        )
        
        opt_lambda, opt_mu = res.x
        probs = self._pois_probs(opt_lambda, opt_mu, 0.0)
        
        return ScoreDist(probs=probs)

    @property
    def model_card(self) -> dict:
        return {
            "name": "Market-Implied",
            "version": "1.0",
            "params": {
                "max_goals": self.max_goals
            }
        }
