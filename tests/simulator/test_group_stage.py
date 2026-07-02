import numpy as np

from wc2026.simulator.group_stage import compute_group_standings, rank_third_placed


def test_compute_group_standings():
    # 2 paths, 6 matches
    # Match order (0,1), (0,2), (0,3), (1,2), (1,3), (2,3)
    matches = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
    
    # Path 0: Team 0 wins all. (3-0, 3-0, 3-0). Team 1 wins remaining (2-0, 2-0). Team 2 wins last (1-0).
    # Path 1: Team 3 wins all.
    home_goals = np.array([
        [3, 3, 3, 2, 2, 1],
        [0, 0, 0, 0, 0, 0]
    ])
    away_goals = np.array([
        [0, 0, 0, 0, 0, 0],
        [3, 3, 3, 3, 3, 3] # Team 1 beats 0, Team 2 beats 0, Team 3 beats 0, Team 2 beats 1, Team 3 beats 1, Team 3 beats 2
    ])
    # Wait, the second path away_goals means:
    # 0 vs 1: 0-3 (Team 1 wins)
    # 0 vs 2: 0-3 (Team 2 wins)
    # 0 vs 3: 0-3 (Team 3 wins)
    # 1 vs 2: 0-3 (Team 2 wins)
    # 1 vs 3: 0-3 (Team 3 wins)
    # 2 vs 3: 0-3 (Team 3 wins)
    # So in Path 1, Team 3 has 3 wins (9 pts). Team 2 has 2 wins (6 pts). Team 1 has 1 win (3 pts). Team 0 has 0 wins.
    
    order, points, gd, gf = compute_group_standings(home_goals, away_goals, matches)
    
    assert points.shape == (2, 4)
    # Path 0: Team 0 (9), Team 1 (6), Team 2 (3), Team 3 (0)
    assert list(points[0]) == [9, 6, 3, 0]
    assert list(order[0]) == [0, 1, 2, 3]
    
    # Path 1: Team 0 (0), Team 1 (3), Team 2 (6), Team 3 (9)
    assert list(points[1]) == [0, 3, 6, 9]
    assert list(order[1]) == [3, 2, 1, 0]

def test_rank_third_placed():
    # 1 path, 12 teams
    points = np.array([[10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0]])
    gd = np.zeros((1, 12))
    gf = np.zeros((1, 12))
    
    order = rank_third_placed(points, gd, gf)
    assert order.shape == (1, 12)
    assert list(order[0]) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] or list(order[0]) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 10]
