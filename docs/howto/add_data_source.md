# How-To: Add a Data Source Ingest Pipeline

This guide outlines the steps to build a new ingestion pipeline, enforcing the **[Fetch/Parse Separation](../adr/0010-fetch-parse-separation.md)** architectural rule.

---

## Step 1: Write the Fetcher (Thin I/O Layer)

Create a fetcher function inside a new module under `src/wc2026/ingest/` (e.g. `src/wc2026/ingest/weather.py`):
- Ensure it is idempotent (checks `RawStore` cache before making requests).
- Write raw payload directly without formatting or parsing.

```python
from datetime import datetime
from pathlib import Path
from wc2026.ingest.base import RawStore, HTTPClient


def fetch_weather_forecast(store: RawStore, client: HTTPClient, city: str, as_of: datetime) -> Path:
    """
    Idempotent raw fetcher. Replay-safe.
    """
    filename = f"weather/{city}_{as_of.strftime('%Y-%m-%d')}.json"
    
    # Idempotent Cache Check
    if store.exists(filename):
        return store.get_path(filename)
        
    url = f"https://api.open-meteo.com/v1/forecast?city={city}"
    response = client.get(url)
    
    # Write Raw String byte-for-byte
    store.write(filename, response.text, as_of=as_of)
    return store.get_path(filename)
```

---

## Step 2: Write the Parser (Pure Function)

- Must have no side effects (no network, filesystem, or database reads/writes).
- Input: raw string/bytes.
- Output: normalized pandas DataFrame.

```python
import json
import pandas as pd


def parse_weather_forecast(raw_payload: str) -> pd.DataFrame:
    """
    Pure parser. Highly testable.
    """
    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        raise ValueError("Malformed JSON payload") from e
        
    # Validate fields
    if "hourly" not in data or "temperature_2m" not in data["hourly"]:
        raise KeyError("Missing 'hourly.temperature_2m' keys in payload")
        
    temps = data["hourly"]["temperature_2m"]
    df = pd.DataFrame({"temp_c": temps})
    return df
```

---

## Step 3: Write Hermetic Unit Tests

- Never make network requests inside the tests.
- Load sample mock outputs from files under `tests/ingest/fixtures/`.

Create `tests/ingest/test_weather.py`:

```python
import pytest
from wc2026.ingest.weather import parse_weather_forecast


@pytest.fixture
def mock_weather_payload():
    return '{"hourly": {"temperature_2m": [18.5, 19.2, 20.1]}}'


def test_parse_weather(mock_weather_payload):
    df = parse_weather_forecast(mock_weather_payload)
    assert len(df) == 3
    assert df["temp_c"].iloc[0] == 18.5
```

---

## Step 4: Write Feature Store Compilation

Wire the parsed fields into [`src/wc2026/features/store.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/features/store.py) with explicit `knowable_at` timestamps:

```python
from wc2026.features.store import FeatureStore

def compile_weather_features(db_path: str, match_id: str, df: pd.DataFrame, kickoff_ts: datetime):
    store = FeatureStore(db_path)
    avg_temp = float(df["temp_c"].mean())
    
    # Upsert with PIT timestamp
    store.upsert(
        match_id=match_id,
        name="avg_temperature_c",
        value=avg_temp,
        knowable_at=kickoff_ts - timedelta(hours=2)  # Forecast published 2 hours before match
    )
```

---

## Step 5: Verification Run

- Verify data contract details inside `docs/data_contracts/`.
- Run the full validation suite:
  ```bash
  make verify
  ```
