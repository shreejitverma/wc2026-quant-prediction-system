import requests_mock

from wc2026.ingest.venues import VenueDataClient


def test_venues():
    client = VenueDataClient()
    
    with requests_mock.Mocker() as m:
        m.get("https://api.open-meteo.com/v1/forecast", json={"daily": {"time": ["2026-01-01"], "temperature_2m_max": [25.0], "precipitation_sum": [1.0]}})
        res = client.fetch_venue_forecast("Mexico City")
        assert res['temp_max_c'] == 25.0
        
        df = client.generate_all_venues_report()
        assert len(df) == 16
        
        assert client.fetch_venue_forecast("Unknown") == {}
