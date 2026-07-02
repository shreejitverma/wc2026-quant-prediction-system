"""Vectorized Knockout Stage Simulation."""

import numpy as np


def simulate_knockout_round(
    home_teams: np.ndarray,  
    away_teams: np.ndarray,  
    home_goals: np.ndarray,  
    away_goals: np.ndarray,  
    home_pen_probs: np.ndarray 
) -> np.ndarray:
    """
    Simulates a single knockout round across N_PATHS.
    
    Args:
        home_teams: (N_PATHS, N_MATCHES) array of team indices.
        away_teams: (N_PATHS, N_MATCHES) array of team indices.
        home_goals: (N_PATHS, N_MATCHES) goals scored by home team (incl. extra time).
        away_goals: (N_PATHS, N_MATCHES) goals scored by away team (incl. extra time).
        home_pen_probs: (N_PATHS, N_MATCHES) probability of home team winning a penalty shootout.
        
    Returns:
        advancing_teams: (N_PATHS, N_MATCHES) array of team indices that advanced.
    """
    home_win = home_goals > away_goals
    draw = home_goals == away_goals
    
    # Simulate penalty shootouts for draws
    rand_pens = np.random.rand(*home_goals.shape)
    home_win_pens = draw & (rand_pens < home_pen_probs)
    
    home_advances = home_win | home_win_pens
    
    advancing_teams = np.where(home_advances, home_teams, away_teams)
    return advancing_teams
