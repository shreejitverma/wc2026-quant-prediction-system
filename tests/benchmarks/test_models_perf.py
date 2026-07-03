from datetime import UTC, datetime

import numpy as np
import pandas as pd

from wc2026.models.base import Model, ScoreDist
from wc2026.models.meta_ensemble import MetaModel


class MockModel(Model):
    def fit(self, match_results: pd.DataFrame, as_of_ts: datetime):
        pass
        
    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        probs = np.zeros((10, 10))
        probs[1, 1] = 0.5
        probs[2, 1] = 0.3
        probs[1, 2] = 0.2
        return ScoreDist(probs=probs)
        
    def model_card(self) -> dict:
        return {"name": "Mock"}

def test_meta_model_fit_perf(benchmark):
    """Benchmark the Log-Loss optimization routine in MetaModel.fit"""
    # Create synthetic dataset of 1000 matches
    n_matches = 1000
    df = pd.DataFrame({
        'date': [datetime(2025, 1, 1, tzinfo=UTC)] * n_matches,
        'home_team': ['TeamA'] * n_matches,
        'away_team': ['TeamB'] * n_matches,
        'home_score': np.random.randint(0, 4, size=n_matches),
        'away_score': np.random.randint(0, 4, size=n_matches),
        'neutral': [False] * n_matches,
    })
    
    models = [MockModel(), MockModel(), MockModel()]
    meta = MetaModel(models, pool_type='log')
    
    benchmark(meta.fit, df, datetime.now(UTC))

def test_meta_model_predict_perf(benchmark):
    """Benchmark the ensembling prediction step"""
    models = [MockModel(), MockModel(), MockModel()]
    meta = MetaModel(models, pool_type='log')
    # Mock weights to skip fitting
    meta.weights = [0.33, 0.33, 0.34]
    
    features = {
        'home_team': 'TeamA',
        'away_team': 'TeamB',
        'neutral': False,
        'elo_home': 1500.0,
        'elo_away': 1500.0
    }
    
    benchmark(meta.predict_match, "TeamA_vs_TeamB", datetime.now(UTC), features)
