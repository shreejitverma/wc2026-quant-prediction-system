"""Feature Store Simulator Bridge."""

from datetime import datetime

import numpy as np

from wc2026.features.store import FeatureStore


class SimulatorBridge:
    """
    Connects the Point-In-Time Feature Store to the Vectorized Simulator.
    """
    def __init__(self, feature_store: FeatureStore):
        self.fs = feature_store

    def build_simulation_context(self, as_of_ts: datetime, teams: list[str]) -> dict:
        """
        Extracts the necessary features for all teams exactly as they were known at `as_of_ts`.
        
        Returns:
            dict containing numpy arrays for Elo, rest days, etc., aligned with `teams`.
        """
        elos = np.zeros(len(teams))
        
        for i, _team in enumerate(teams):
            # For each team, we query the PIT feature store.
            # In a real implementation, we'd batch this query.
            # team_features = self.fs.get_features(team, as_of_ts)
            # elos[i] = team_features.get('elo', 1500.0)
            
            # Mock extraction
            elos[i] = 1500.0
            
        return {
            'elos': elos,
            'teams': teams,
            'as_of_ts': as_of_ts
        }
