from datetime import datetime

import pandas as pd
import pytest

from wc2026.models.dixon_coles import DixonColesModel


def test_dixon_coles_fit_and_predict():
    # Create dummy match results
    df = pd.DataFrame({
        'date': [
            datetime(2026, 1, 1),
            datetime(2026, 1, 2),
            datetime(2026, 1, 3),
            datetime(2026, 1, 4),
        ],
        'home_team': ['A', 'B', 'C', 'A'],
        'away_team': ['B', 'C', 'A', 'C'],
        'home_score': [2, 1, 0, 3],
        'away_score': [0, 1, 2, 1],
        'neutral': [False, False, False, True]
    })
    
    model = DixonColesModel(max_goals=5, time_decay_tau=0.0)
    model.fit(df, as_of_ts=datetime(2026, 2, 1))
    
    # Check parameters fitted
    assert len(model.teams) == 3
    assert len(model.alphas) == 3
    assert len(model.betas) == 3
    
    # Predict
    features = {'home_team': 'A', 'away_team': 'B', 'neutral': False}
    dist = model.predict_match('m1', datetime(2026, 2, 1), features)
    
    assert dist.max_goals == 5
    assert pytest.approx(dist.probs.sum()) == 1.0
    assert dist.p_home_win() >= 0.0
    assert dist.p_draw() >= 0.0
    assert dist.p_away_win() >= 0.0

def test_dc_tau_matrix():
    model = DixonColesModel()
    tau = model._tau_matrix(1.5, 1.2, 0.1)
    
    assert tau[0, 0] == 1.0 - 1.5 * 1.2 * 0.1
    assert tau[0, 1] == 1.0 + 1.5 * 0.1
    assert tau[1, 0] == 1.0 + 1.2 * 0.1
    assert tau[1, 1] == 1.0 - 0.1
    
    # other values should be 1.0
    assert tau[2, 2] == 1.0
