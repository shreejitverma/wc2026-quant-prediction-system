"""Quoting Engine based on Avellaneda-Stoikov."""

import numpy as np


class QuotingEngine:
    """
    Computes Reservation Price and Spread for Market Making.
    Adapted for binary prediction markets.
    """
    def __init__(self, risk_aversion: float = 0.1, arrival_rate: float = 1.5):
        self.gamma = risk_aversion
        self.k = arrival_rate
        
    def compute_quotes(self, fair_value: float, inventory: float, variance: float, time_to_settlement: float) -> tuple[float, float]:
        """
        Calculates optimal bid and ask using Avellaneda-Stoikov.
        
        Args:
            fair_value: True probability / mid price.
            inventory: Current net position (e.g. +100 means long 100 contracts).
            variance: Volatility of the asset (for binary it's p*(1-p) usually).
            time_to_settlement: Time remaining in days/years.
            
        Returns:
            (bid, ask) tuple, bounded between [0.01, 0.99]
        """
        # Reservation price shifts midpoint away from our inventory risk
        r = fair_value - self.gamma * variance * inventory * time_to_settlement
        
        # Spread depends on time and arrival rate
        spread = self.gamma * variance * time_to_settlement + (2.0 / self.gamma) * np.log(1.0 + self.gamma / self.k)
        
        bid = r - spread / 2.0
        ask = r + spread / 2.0
        
        return max(0.01, min(0.99, bid)), max(0.01, min(0.99, ask))
