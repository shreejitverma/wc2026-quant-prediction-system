"""Base interfaces for the model suite."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class ScoreDist:
    """Joint probability distribution over match scorelines."""
    # 2D array: probs[home_goals, away_goals]
    probs: np.ndarray

    def __post_init__(self):
        if self.probs.ndim != 2 or self.probs.shape[0] != self.probs.shape[1]:
            raise ValueError("probs must be a square 2D numpy array.")
        total = self.probs.sum()
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Probabilities must sum to ~1.0, got {total:.4f}")

    @property
    def max_goals(self) -> int:
        return self.probs.shape[0] - 1

    def p_home_win(self) -> float:
        return float(np.tril(self.probs, -1).sum())

    def p_draw(self) -> float:
        return float(np.trace(self.probs))

    def p_away_win(self) -> float:
        return float(np.triu(self.probs, 1).sum())

    def p_home_goals(self, k: int) -> float:
        if k < 0 or k > self.max_goals:
            return 0.0
        return float(self.probs[k, :].sum())

    def p_away_goals(self, k: int) -> float:
        if k < 0 or k > self.max_goals:
            return 0.0
        return float(self.probs[:, k].sum())

    def p_over(self, goals: float) -> float:
        """Probability of strictly more than `goals` total goals (e.g. 2.5)."""
        idx = np.indices(self.probs.shape)
        total_goals = idx[0] + idx[1]
        return float(self.probs[total_goals > goals].sum())

    def p_under(self, goals: float) -> float:
        """Probability of strictly fewer than `goals` total goals (e.g. 2.5)."""
        idx = np.indices(self.probs.shape)
        total_goals = idx[0] + idx[1]
        return float(self.probs[total_goals < goals].sum())


class Model(ABC):
    @abstractmethod
    def fit(self, match_results: pd.DataFrame, as_of_ts: datetime):
        """
        Fit the model on historical results.
        
        Args:
            match_results: DataFrame with historical match results up to as_of_ts.
            as_of_ts: The point in time we are fitting for (to compute time decay, etc).
        """
        pass

    @abstractmethod
    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        """
        Predict the full scoreline distribution for a given match.
        
        Args:
            match_id: String ID of the match.
            as_of_ts: The point in time we are predicting from.
            features: Point-in-time correct features dictionary.
        """
        pass

    @property
    @abstractmethod
    def model_card(self) -> dict:
        """Metadata and parameters describing this model instance."""
        pass
