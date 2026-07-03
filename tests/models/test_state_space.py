from datetime import UTC, datetime

import pandas as pd

from wc2026.models.state_space import DynamicStateSpaceModel


def test_state_space():
    m = DynamicStateSpaceModel()
    df = pd.DataFrame({
        'date': [datetime(2025,1,1, tzinfo=UTC)],
        'home_team': ['A'],
        'away_team': ['B'],
        'home_score': [1],
        'away_score': [0],
        'neutral': [False]
    })
    m.fit(df, datetime(2026,1,1, tzinfo=UTC))
    dist = m.predict_match('A_B', datetime(2026,1,1, tzinfo=UTC), {'home_team':'A', 'away_team':'B'})
    assert dist.probs.shape == (15, 15)
    c = m.model_card()
    assert c['name'] == 'DynamicStateSpaceModel'
