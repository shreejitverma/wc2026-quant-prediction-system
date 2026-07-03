from datetime import UTC, datetime

import pandas as pd

from wc2026.models.player_agg import PlayerAggregationModel


def test_player_agg():
    m = PlayerAggregationModel()
    m.fit(pd.DataFrame(), datetime(2026,1,1, tzinfo=UTC))
    dist = m.predict_match('A_B', datetime(2026,1,1, tzinfo=UTC), {'home_team':'A', 'away_team':'B'})
    assert dist.probs.shape == (15, 15)
    c = m.model_card()
    assert c['name'] == 'PlayerAggregationModel'
