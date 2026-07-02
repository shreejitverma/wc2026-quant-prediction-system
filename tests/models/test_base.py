import numpy as np
import pytest

from wc2026.models.base import ScoreDist


def test_score_dist_validation():
    # Valid
    probs = np.zeros((11, 11))
    probs[1, 2] = 1.0
    sd = ScoreDist(probs)
    assert sd.max_goals == 10

    # Invalid sum
    probs[1, 2] = 0.5
    with pytest.raises(ValueError):
        ScoreDist(probs)

    # Invalid shape
    with pytest.raises(ValueError):
        ScoreDist(np.array([1.0]))

def test_score_dist_probabilities():
    probs = np.zeros((3, 3))
    # Home win
    probs[2, 0] = 0.4
    probs[1, 0] = 0.1
    # Draw
    probs[1, 1] = 0.2
    # Away win
    probs[0, 1] = 0.3
    
    sd = ScoreDist(probs)
    assert pytest.approx(sd.p_home_win()) == 0.5
    assert pytest.approx(sd.p_draw()) == 0.2
    assert pytest.approx(sd.p_away_win()) == 0.3

    assert pytest.approx(sd.p_home_goals(1)) == 0.3  # probs[1,0] + probs[1,1]
    assert pytest.approx(sd.p_away_goals(1)) == 0.5  # probs[0,1] + probs[1,1]

    assert pytest.approx(sd.p_over(1.5)) == 0.6 # 2-0, 1-1
    assert pytest.approx(sd.p_under(1.5)) == 0.4 # 1-0, 0-1
