from datetime import datetime

import pytest

from wc2026.models.market_implied import MarketImpliedModel


def test_market_implied_predict():
    model = MarketImpliedModel(max_goals=5)
    
    features = {
        'market_p_home': 0.5,
        'market_p_draw': 0.25,
        'market_p_away': 0.25
    }
    
    dist = model.predict_match('m1', datetime(2026, 6, 1), features)
    
    assert dist.max_goals == 5
    
    # Output should closely match the inputs
    assert abs(dist.p_home_win() - 0.5) < 0.05
    assert abs(dist.p_draw() - 0.25) < 0.05
    assert abs(dist.p_away_win() - 0.25) < 0.05

def test_market_implied_missing_features():
    model = MarketImpliedModel()
    with pytest.raises(ValueError):
        model.predict_match('m1', datetime(2026, 6, 1), {'market_p_home': 0.5})
