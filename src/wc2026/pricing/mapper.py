"""Contract mapping and parsing logic."""

class EventType:
    ADVANCES = "ADVANCES"
    WINS_TOURNAMENT = "WINS_TOURNAMENT"
    REACHES_FINAL = "REACHES_FINAL"
    WINS_GROUP = "WINS_GROUP"
    WINS_MATCH = "WINS_MATCH"
    UNKNOWN = "UNKNOWN"

class ContractMapper:
    """Maps Kalshi/Polymarket contracts to precise model events."""
    
    @staticmethod
    def parse_kalshi_ticker(ticker: str) -> dict:
        """
        Parses a Kalshi ticker for WC2026 into a structured event definition.
        Example: KXWCADVANCE-MEX -> {'type': EventType.ADVANCES, 'team': 'MEX'}
        """
        if ticker.startswith("KXWCADVANCE-"):
            team = ticker.split("-")[1]
            return {"type": EventType.ADVANCES, "team": team}
        elif ticker.startswith("KXWCWIN-"):
            team = ticker.split("-")[1]
            return {"type": EventType.WINS_TOURNAMENT, "team": team}
        elif ticker.startswith("KXWCGRP-"):
            team = ticker.split("-")[1]
            return {"type": EventType.WINS_GROUP, "team": team}
        
        return {"type": EventType.UNKNOWN, "raw": ticker}
