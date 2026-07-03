from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from wc2026.models.base import Model, ScoreDist
from wc2026.models.meta_ensemble import MetaModel


class DummyModel(Model):
    def fit(self, df, as_of_ts):
        pass
    def predict_match(self, match_id, as_of_ts, features):
        prob = np.zeros((3, 3))
        prob[1, 0] = 1.0 # Home win
        return ScoreDist(probs=prob)
    def model_card(self):
        return {"name": "Dummy"}

class DummyModel2(Model):
    def fit(self, df, as_of_ts):
        pass
    def predict_match(self, match_id, as_of_ts, features):
        if match_id == "error_vs_B":
            raise ValueError("test error")
        prob = np.zeros((3, 3))
        prob[0, 1] = 1.0 # Away win
        return ScoreDist(probs=prob)
    def model_card(self):
        return {"name": "Dummy2"}

def test_meta_ensemble_small_data():
    m1 = DummyModel()
    m2 = DummyModel2()
    meta = MetaModel([m1, m2], pool_type='linear')
    df = pd.DataFrame({'a': range(10)}) # len < 50
    meta.fit(df, datetime(2026,1,1, tzinfo=UTC))
    assert meta.weights == [0.5, 0.5]
    
def test_meta_ensemble_large_data():
    m1 = DummyModel()
    m2 = DummyModel2()
    meta = MetaModel([m1, m2], pool_type='log', holdout_frac=0.2)
    df = pd.DataFrame({
        'home_team': ['A'] * 100,
        'away_team': ['B'] * 100,
        'home_score': [2] * 100,
        'away_score': [1] * 100,
        'neutral': [False] * 100,
        'date': [datetime(2026, 1, 1, tzinfo=UTC)] * 100
    })
    
    meta.fit(df, datetime(2026,1,2, tzinfo=UTC))
    assert np.isclose(sum(meta.weights), 1.0)
    
    # Test predict
    dist = meta.predict_match('A_vs_B', datetime(2026,1,3,tzinfo=UTC), {})
    assert dist.probs.shape == (3, 3)
    
    # test linear
    meta.pool_type = 'linear'
    dist2 = meta.predict_match('A_vs_B', datetime(2026,1,3,tzinfo=UTC), {})
    assert dist2.probs.shape == (3, 3)
    
    # test error pool
    meta.pool_type = 'unknown'
    with pytest.raises(ValueError):
        meta.predict_match('A_vs_B', datetime(2026,1,3,tzinfo=UTC), {})
        
def test_meta_ensemble_error_handling():
    m1 = DummyModel()
    m2 = DummyModel2()
    meta = MetaModel([m1, m2], pool_type='linear')
    df = pd.DataFrame({
        'home_team': ['A'] * 100,
        'away_team': ['B'] * 100,
        'home_score': [2] * 100,
        'away_score': [1] * 100,
        'neutral': [False] * 100,
        'date': [datetime(2026, 1, 1, tzinfo=UTC)] * 100
    })
    # inject error in holdout
    df.loc[99, 'home_team'] = 'error'
    meta.fit(df, datetime(2026,1,2, tzinfo=UTC))
    card = meta.model_card()
    assert card['type'] == 'Ensemble'
