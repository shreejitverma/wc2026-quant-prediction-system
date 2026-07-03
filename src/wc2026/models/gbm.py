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
    Uses Elo difference, neutrality, and home advantage to capture non-linearities.
    """
    def __init__(self, max_goals: int = 15, num_leaves: int = 15, learning_rate: float = 0.05):
        self.max_goals = max_goals
        self.params = {
            'objective': 'poisson',
            'num_leaves': num_leaves,
            'learning_rate': learning_rate,
            'verbose': -1,
            'bagging_fraction': 0.8,
            'feature_fraction': 0.9,
            'min_data_in_leaf': 20
        }
        self.model = None

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        # We expect df to potentially have 'elo_home' and 'elo_away'. If not, we impute.
        if 'elo_home' not in df.columns:
            df['elo_home'] = 1300.0
        if 'elo_away' not in df.columns:
            df['elo_away'] = 1300.0
            
        df['elo_diff'] = df['elo_home'] - df['elo_away']

        # Flatten matches into team-level observations
        home_obs = pd.DataFrame({
            'team': df['home_team'],
            'opp': df['away_team'],
            'is_home': 1,
            'neutral': df['neutral'].astype(int),
            'elo_diff': df['elo_diff'],
            'goals': df['home_score']
        })
        away_obs = pd.DataFrame({
            'team': df['away_team'],
            'opp': df['home_team'],
            'is_home': 0,
            'neutral': df['neutral'].astype(int),
            'elo_diff': -df['elo_diff'],
            'goals': df['away_score']
        })
        
        train_df = pd.concat([home_obs, away_obs], ignore_index=True)
        
        # Features used for prediction
        features = ['is_home', 'neutral', 'elo_diff']
            
        X = train_df[features].astype(float)
        y = train_df['goals']
        
        dtrain = lgb.Dataset(X, label=y)
        self.model = lgb.train(self.params, dtrain, num_boost_round=150)

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        if self.model is None:
            raise ValueError("Model not fitted")
            
        neutral = features.get('neutral', False)
        
        elo_home = features.get('elo_home', 1300.0)
        elo_away = features.get('elo_away', 1300.0)
        elo_diff = elo_home - elo_away
        
        # Predict home goals
        # Features: is_home, neutral, elo_diff
        X_home = np.array([[1.0, float(neutral), float(elo_diff)]])
        exp_hg = self.model.predict(X_home)[0]
        
        # Predict away goals
        X_away = np.array([[0.0, float(neutral), float(-elo_diff)]])
        exp_ag = self.model.predict(X_away)[0]
        
        prob_matrix = np.zeros((self.max_goals, self.max_goals))
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                prob_matrix[i, j] = poisson.pmf(i, exp_hg) * poisson.pmf(j, exp_ag)
                
        prob_matrix /= prob_matrix.sum()
        return ScoreDist(probs=prob_matrix)

    def model_card(self) -> dict:
        return {
            "name": "LightGBMModel",
            "type": "GradientBoosting",
            "fitted": self.model is not None,
            "params": self.params
        }
