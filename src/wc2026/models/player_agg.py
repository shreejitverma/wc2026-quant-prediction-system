"""Player-Aggregation Squad Model."""

from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import poisson

from wc2026.models.base import Model, ScoreDist


class PlayerAggregationModel(Model):
    """
    Bottom-up model that aggregates player-level club data into national team strength.
    Requires FBref / StatsBomb data ingestion (Phase 1 Tier 2).
    """
    def __init__(self, max_goals: int = 15):
        self.max_goals = max_goals
        self.team_strengths = {}

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        """
        In the real pipeline, df would contain lineup data or player-level data.
        For now, this is a skeleton waiting for Tier 2 data.
        """
        pass

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        """
        Uses expected lineups (or confirmed XI if close to kickoff) to sum player strengths.
        """
        home = features.get('home_team', 'Unknown')
        away = features.get('away_team', 'Unknown')
        
        # Placeholder logic: without player data, just assume 1.1 xG per team
        exp_hg = 1.1
        exp_ag = 1.1
        
        prob_matrix = np.zeros((self.max_goals, self.max_goals))
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                prob_matrix[i, j] = poisson.pmf(i, exp_hg) * poisson.pmf(j, exp_ag)
                
        return ScoreDist(home_team=home, away_team=away, prob_matrix=prob_matrix)

    def model_card(self) -> dict:
        return {
            "name": "PlayerAggregationModel",
            "type": "BottomUp",
            "data_dependency": "Tier2"
        }
