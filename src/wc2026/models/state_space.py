"""Dynamic State-Space Goal Ratings."""

from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import poisson

from wc2026.models.base import Model, ScoreDist


class DynamicStateSpaceModel(Model):
    """
    Implements a recursive filter (Elo-like but for expected goals).
    """
    def __init__(self, max_goals: int = 15, learning_rate: float = 0.05, home_adv: float = 0.2):
        self.max_goals = max_goals
        self.learning_rate = learning_rate
        self.home_adv = home_adv
        self.ratings = {} # team -> {'att': 0.0, 'def': 0.0}

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        # Sort chronologically to simulate time-series filtering
        df = df.sort_values('date')
        
        self.ratings = {}
        
        # We process matches sequentially and update ratings
        for _, row in df.iterrows():
            if pd.to_datetime(row['date'], utc=True) > pd.to_datetime(as_of_ts, utc=True):
                continue
                
            home = row['home_team']
            away = row['away_team']
            hg = row['home_score']
            ag = row['away_score']
            neutral = row['neutral']
            
            if home not in self.ratings:
                self.ratings[home] = {'att': 0.0, 'def': 0.0}
            if away not in self.ratings:
                self.ratings[away] = {'att': 0.0, 'def': 0.0}
                
            h_att = self.ratings[home]['att']
            h_def = self.ratings[home]['def']
            a_att = self.ratings[away]['att']
            a_def = self.ratings[away]['def']
            
            # Predict
            h_adv = self.home_adv if not neutral else 0.0
            expected_hg = np.exp(h_att - a_def + h_adv)
            expected_ag = np.exp(a_att - h_def)
            
            # Update (Gradient descent step on Poisson log-likelihood)
            # Poisson log likelihood grad w.r.t log(lambda): y - lambda
            h_err = hg - expected_hg
            a_err = ag - expected_ag
            
            self.ratings[home]['att'] += self.learning_rate * h_err
            self.ratings[away]['def'] -= self.learning_rate * h_err
            
            self.ratings[away]['att'] += self.learning_rate * a_err
            self.ratings[home]['def'] -= self.learning_rate * a_err

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        home = features.get('home_team', 'Unknown')
        away = features.get('away_team', 'Unknown')
        neutral = features.get('neutral', False)
        
        h_att = self.ratings.get(home, {}).get('att', 0.0)
        h_def = self.ratings.get(home, {}).get('def', 0.0)
        a_att = self.ratings.get(away, {}).get('att', 0.0)
        a_def = self.ratings.get(away, {}).get('def', 0.0)
        
        h_adv = self.home_adv if not neutral else 0.0
        
        expected_hg = np.exp(h_att - a_def + h_adv)
        expected_ag = np.exp(a_att - h_def)
        
        # Create independent Poisson distribution matrix
        prob_matrix = np.zeros((self.max_goals, self.max_goals))
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                prob_matrix[i, j] = poisson.pmf(i, expected_hg) * poisson.pmf(j, expected_ag)
                
        return ScoreDist(home_team=home, away_team=away, prob_matrix=prob_matrix)

    def model_card(self) -> dict:
        return {
            "name": "DynamicStateSpaceModel",
            "type": "RecursiveFilter",
            "learning_rate": self.learning_rate
        }
