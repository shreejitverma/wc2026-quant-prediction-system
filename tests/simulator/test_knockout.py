import numpy as np

from wc2026.simulator.knockout import simulate_knockout_round


def test_simulate_knockout_round():
    home_teams = np.array([[0, 2], [10, 12]])
    away_teams = np.array([[1, 3], [11, 13]])
    
    # Path 0: Home wins match 0 (2-1), Away wins match 1 (0-1)
    # Path 1: Draws both (1-1, 0-0)
    home_goals = np.array([[2, 0], [1, 0]])
    away_goals = np.array([[1, 1], [1, 0]])
    
    # Path 1: home_pen_probs: match 0 is 1.0 (home always wins), match 1 is 0.0 (away always wins)
    home_pen_probs = np.array([[0.5, 0.5], [1.0, 0.0]])
    
    advancing = simulate_knockout_round(home_teams, away_teams, home_goals, away_goals, home_pen_probs)
    
    assert advancing.shape == (2, 2)
    
    # Path 0
    assert advancing[0, 0] == 0  # home won
    assert advancing[0, 1] == 3  # away won
    
    # Path 1
    assert advancing[1, 0] == 10 # draw, home won pens
    assert advancing[1, 1] == 13 # draw, away won pens
