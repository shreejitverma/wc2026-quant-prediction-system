"""Venue and Weather Data Ingestion."""

import logging
from datetime import UTC, datetime

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Hardcoded 2026 World Cup Venues with Lat/Lon and Base Altitude (meters)
VENUES = {
    "Mexico City": {"lat": 19.3029, "lon": -99.1505, "altitude": 2240},
    "Guadalajara": {"lat": 20.6817, "lon": -103.4628, "altitude": 1566},
    "Monterrey": {"lat": 25.6698, "lon": -100.2444, "altitude": 540},
    "Vancouver": {"lat": 49.2768, "lon": -123.1120, "altitude": 10},
    "Toronto": {"lat": 43.6332, "lon": -79.4186, "altitude": 75},
    "New York/New Jersey": {"lat": 40.8128, "lon": -74.0742, "altitude": 2},
    "Dallas": {"lat": 32.7473, "lon": -97.0945, "altitude": 165},
    "Kansas City": {"lat": 39.0489, "lon": -94.4839, "altitude": 269},
    "Houston": {"lat": 29.6847, "lon": -95.4107, "altitude": 15},
    "Atlanta": {"lat": 33.7550, "lon": -84.4008, "altitude": 300},
    "Los Angeles": {"lat": 33.9534, "lon": -118.3387, "altitude": 30},
    "Philadelphia": {"lat": 39.9008, "lon": -75.1675, "altitude": 5},
    "Seattle": {"lat": 47.5952, "lon": -122.3316, "altitude": 5},
    "San Francisco": {"lat": 37.4030, "lon": -121.9698, "altitude": 10},
    "Boston": {"lat": 42.0909, "lon": -71.2643, "altitude": 45},
    "Miami": {"lat": 25.9580, "lon": -80.2389, "altitude": 2}
}

class VenueDataClient:
    """
    Fetches real-time weather forecasts for World Cup venues.
    Uses Open-Meteo (no API key required).
    """
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.session = requests.Session()

    def fetch_venue_forecast(self, venue_name: str) -> dict:
        """
        Fetches the current 7-day forecast for a venue.
        Returns expected temperature, humidity, and precipitation.
        """
        if venue_name not in VENUES:
            logger.error(f"Unknown venue: {venue_name}")
            return {}

        venue = VENUES[venue_name]
        
        params = {
            "latitude": venue["lat"],
            "longitude": venue["lon"],
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "auto"
        }

        try:
            resp = self.session.get(self.base_url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract today's forecast
            daily = data.get("daily", {})
            if "time" in daily and len(daily["time"]) > 0:
                return {
                    "altitude": venue["altitude"],
                    "temp_max_c": daily.get("temperature_2m_max", [None])[0],
                    "precip_mm": daily.get("precipitation_sum", [None])[0]
                }
            return {"altitude": venue["altitude"]}

        except Exception as e:
            logger.error(f"Failed to fetch weather for {venue_name}: {e}")
            return {"altitude": venue["altitude"]}

    def generate_all_venues_report(self) -> pd.DataFrame:
        """
        Builds a DataFrame containing current conditions for all venues.
        Useful for batch updating the Point-In-Time Feature Store.
        """
        results = []
        for name in VENUES.keys():
            forecast = self.fetch_venue_forecast(name)
            results.append({
                "venue": name,
                "altitude": forecast.get("altitude"),
                "temp_max_c": forecast.get("temp_max_c"),
                "precip_mm": forecast.get("precip_mm"),
                "timestamp": datetime.now(UTC).isoformat()
            })
            
        return pd.DataFrame(results)
