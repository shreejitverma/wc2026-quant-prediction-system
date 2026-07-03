from datetime import UTC, datetime

import pandas as pd
import pytest

from wc2026.models.gbm import GBMModel


def test_gbm_model():
    model = GBMModel(max_goals=3, num_leaves=2, learning_rate=0.1)
    df = pd.DataFrame({
        'home_team': ['A', 'B'],
        'away_team': ['B', 'A'],
        'home_score': [2, 1],
        'away_score': [1, 2],
        'neutral': [False, True],
        'date': [datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)]
    })
    
    # Test un-fitted predict error
    with pytest.raises(ValueError):
        model.predict_match('A_vs_B', datetime(2026,1,3, tzinfo=UTC), {})

    model.fit(df, datetime(2026,1,3, tzinfo=UTC))
    
    card = model.model_card()
    assert card['name'] == 'LightGBMModel'
    assert card['fitted'] is True
    
    # Predict
    features = {
        'home_team': 'A',
        'away_team': 'B',
        'neutral': False,
        'elo_home': 1400.0,
        'elo_away': 1300.0
    }
    
    dist = model.predict_match('A_vs_B', datetime(2026,1,3, tzinfo=UTC), features)
    assert dist.probs.shape == (3, 3)
