from datetime import UTC, datetime

import numpy as np
import pandas as pd

from wc2026.eval.backtest import WalkForwardBacktester
from wc2026.models.base import Model, ScoreDist


class DummyModel(Model):
    def fit(self, df, as_of_ts): pass
    def predict_match(self, match_id, as_of_ts, features):
        if "err" in match_id:
            raise ValueError()
        prob = np.zeros((3, 3))
        prob[1, 0] = 1.0
        return ScoreDist(probs=prob)
    def model_card(self): return {}

def test_backtester_empty():
    bt = WalkForwardBacktester([DummyModel()])
    df = pd.DataFrame({'date': []})
    res = bt.run(df, datetime(2026,1,1, tzinfo=UTC), datetime(2026,1,2, tzinfo=UTC))
    assert res['matches_evaluated'] == 0

def test_backtester_run():
    bt = WalkForwardBacktester([DummyModel()])
    df = pd.DataFrame({
        'date': [datetime(2025,1,1, tzinfo=UTC), datetime(2026,1,1, tzinfo=UTC), datetime(2026,1,2, tzinfo=UTC)],
        'home_team': ['A', 'A', 'err'],
        'away_team': ['B', 'B', 'B'],
        'home_score': [1, 1, 0],
        'away_score': [0, 0, 0],
        'neutral': [False, False, False]
    })
    res = bt.run(df, datetime(2026,1,1, tzinfo=UTC), datetime(2026,1,3, tzinfo=UTC))
    assert res['matches_evaluated'] > 0
    assert 'log_loss' in res
