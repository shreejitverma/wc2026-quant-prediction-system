"""LightGBM Goal Predictor."""
from datetime import datetime

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import poisson

from wc2026.models.base import Model, ScoreDist


class GBMModel(Model):
    """
    Predicts expected goals using Gradient Boosting Trees.
    Allows easy non-linear interactions between features like Elo, fatigue, and altitude.
    """
    def __init__(self, max_goals: int = 15, num_leaves: int = 31, learning_rate: float = 0.05):
        self.max_goals = max_goals
        self.params = {
            'objective': 'poisson',
            'num_leaves': num_leaves,
            'learning_rate': learning_rate,
            'verbose': -1
        }
        self.model = None

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        # Flatten matches into team-level observations
        home_obs = pd.DataFrame({
            'team': df['home_team'],
            'opp': df['away_team'],
            'is_home': 1,
            'neutral': df['neutral'],
            'goals': df['home_score']
        })
        away_obs = pd.DataFrame({
            'team': df['away_team'],
            'opp': df['home_team'],
            'is_home': 0,
            'neutral': df['neutral'],
            'goals': df['away_score']
        })
        
        train_df = pd.concat([home_obs, away_obs], ignore_index=True)
        
        # Features used for prediction
        # In a fully integrated pipeline, this would extract 'team_elo_diff', 'rest_days', etc.
        features = ['is_home', 'neutral']
            
        X = train_df[features].astype(float)
        y = train_df['goals']
        
        dtrain = lgb.Dataset(X, label=y)
        self.model = lgb.train(self.params, dtrain, num_boost_round=100)

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        if self.model is None:
            raise ValueError("Model not fitted")
            
        home = features.get('home_team', 'Unknown')
        away = features.get('away_team', 'Unknown')
        neutral = features.get('neutral', False)
        
        # Predict home goals
        X_home = np.array([[1.0, float(neutral)]])
        exp_hg = self.model.predict(X_home)[0]
        
        # Predict away goals
        X_away = np.array([[0.0, float(neutral)]])
        exp_ag = self.model.predict(X_away)[0]
        
        prob_matrix = np.zeros((self.max_goals, self.max_goals))
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                prob_matrix[i, j] = poisson.pmf(i, exp_hg) * poisson.pmf(j, exp_ag)
                
        return ScoreDist(home_team=home, away_team=away, prob_matrix=prob_matrix)

    def model_card(self) -> dict:
        return {
            "name": "LightGBMModel",
            "type": "GradientBoosting",
            "fitted": self.model is not None
        }
