"""Vectorized Group Stage Simulation."""


import numpy as np


def compute_group_standings(
    home_goals: np.ndarray, 
    away_goals: np.ndarray,
    matches: list[tuple[int, int]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes standings for a single group across N_PATHS.
    
    Args:
        home_goals: (N_PATHS, 6) array of goals scored by home team in each of 6 matches
        away_goals: (N_PATHS, 6) array of goals scored by away team in each of 6 matches
        matches: list of 6 tuples, where each tuple is (home_team_idx, away_team_idx)
                 The team_idx should be 0, 1, 2, 3 for the 4 teams in the group.
             
    Returns:
        ranks: (N_PATHS, 4) containing the team indices (0-3) in order from 1st to 4th.
        points: (N_PATHS, 4)
        gd: (N_PATHS, 4)
        gf: (N_PATHS, 4)
    """
    n_paths = home_goals.shape[0]
    
    points = np.zeros((n_paths, 4), dtype=np.int32)
    gd = np.zeros((n_paths, 4), dtype=np.int32)
    gf = np.zeros((n_paths, 4), dtype=np.int32)
    
    for match_idx, (h_idx, a_idx) in enumerate(matches):
        hg = home_goals[:, match_idx]
        ag = away_goals[:, match_idx]
        
        # GF
        gf[:, h_idx] += hg
        gf[:, a_idx] += ag
        
        # GD
        gd[:, h_idx] += (hg - ag)
        gd[:, a_idx] += (ag - hg)
        
        # Points
        home_win = hg > ag
        away_win = ag > hg
        draw = hg == ag
        
        points[:, h_idx] += (home_win * 3 + draw * 1)
        points[:, a_idx] += (away_win * 3 + draw * 1)

    # Sort using lexsort. 
    # np.lexsort sorts by the last key first, so we reverse the order of importance.
    # Tiebreakers: 1) Points, 2) GD, 3) GF, 4) Random.
    # Since lexsort sorts ascending, we negate points, gd, gf to get descending order.
    
    # We add a small random tiebreaker to ensure deterministic output for equal stats
    random_tiebreaker = np.random.rand(n_paths, 4)
    
    # We want to sort the indices (0,1,2,3).
    # lexsort keys: (random_tiebreaker, -gf, -gd, -points)
    # The last element in the tuple is the primary sort key
    order = np.lexsort((random_tiebreaker, -gf, -gd, -points), axis=1)
    
    return order, points, gd, gf

def rank_third_placed(
    points: np.ndarray,
    gd: np.ndarray,
    gf: np.ndarray
) -> np.ndarray:
    """
    Ranks the 12 third-placed teams across N_PATHS.
    
    Args:
        points: (N_PATHS, 12)
        gd: (N_PATHS, 12)
        gf: (N_PATHS, 12)
        
    Returns:
        order: (N_PATHS, 12) array of indices (0-11) sorted 1st to 12th.
               The top 8 indices in each row advance to the knockout stage.
    """
    n_paths = points.shape[0]
    random_tiebreaker = np.random.rand(n_paths, 12)
    order = np.lexsort((random_tiebreaker, -gf, -gd, -points), axis=1)
    return order
