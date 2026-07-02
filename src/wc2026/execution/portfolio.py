"""Convex Portfolio Optimizer."""

import cvxpy as cp
import numpy as np


class PortfolioOptimizer:
    """
    Maximizes expected edge subject to variance and position limits.
    """
    def __init__(self, risk_budget: float, per_event_limit: float):
        self.risk_budget = risk_budget
        self.per_event_limit = per_event_limit
        
    def optimize(self, expected_edges: np.ndarray, covariance_matrix: np.ndarray) -> np.ndarray:
        """
        Expected_edges: shape (N,)
        covariance_matrix: shape (N, N) from the Simulator's joint draws.
        
        Returns:
            Optimal positions: shape (N,)
        """
        n_assets = len(expected_edges)
        
        # Variables
        w = cp.Variable(n_assets)
        
        # Objective: Maximize expected edge
        objective = cp.Maximize(expected_edges @ w)
        
        # Constraints
        constraints = [
            cp.quad_form(w, covariance_matrix) <= self.risk_budget,
            cp.abs(w) <= self.per_event_limit
        ]
        
        # Problem
        prob = cp.Problem(objective, constraints)
        
        # Solve using OSQP or SCS
        prob.solve(solver=cp.OSQP)
        
        if w.value is None:
            return np.zeros(n_assets)
            
        return w.value
