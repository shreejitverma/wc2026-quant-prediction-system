"""System Kill Switches."""

from datetime import datetime


class KillSwitches:
    """
    Safety checks that evaluate whether to pull all quotes immediately.
    """
    def __init__(self, max_data_staleness_sec: int = 120, max_drawdown_usd: float = 250.0):
        self.max_staleness = max_data_staleness_sec
        self.max_drawdown = max_drawdown_usd
        
    def evaluate(self, last_data_ts: datetime, current_ts: datetime, current_drawdown: float) -> tuple[bool, str]:
        """
        Returns (should_kill, reason).
        """
        staleness = (current_ts - last_data_ts).total_seconds()
        
        if staleness > self.max_staleness:
            return True, f"Data stale by {staleness}s (max {self.max_staleness})"
            
        if current_drawdown > self.max_drawdown:
            return True, f"Drawdown {current_drawdown} exceeds limit {self.max_drawdown}"
            
        return False, "OK"
