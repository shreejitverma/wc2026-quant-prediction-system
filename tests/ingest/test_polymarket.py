import json
import tempfile
from unittest.mock import MagicMock, patch

from wc2026.ingest.base import HTTPClient, RawStore
from wc2026.ingest.polymarket import (
    fetch_clob_orderbook,
    fetch_market_by_slug,
    fetch_wc_events,
    parse_clob_orderbook,
    parse_events,
)


@patch('httpx.Client.get')
def test_polymarket_fetch(mock_get):
    with tempfile.TemporaryDirectory() as td:
        store = RawStore(td)
        with HTTPClient(store, min_request_interval=0.0) as client:
            resp1 = MagicMock()
            resp1.status_code = 200
            resp1.content = json.dumps([{"id": "1"}]).encode()
            mock_get.return_value = resp1
            res = fetch_wc_events(client, store)
            assert len(res) > 0
            
            resp2 = MagicMock()
            resp2.status_code = 200
            resp2.content = json.dumps([{"slug": "test"}]).encode()
            mock_get.return_value = resp2
            p2 = fetch_market_by_slug(client, store, "test")
            assert p2.exists()
            
            resp3 = MagicMock()
            resp3.status_code = 200
            resp3.content = json.dumps({"bids": [{"price": "0.4", "size": "100"}], "asks": [{"price": "0.6", "size": "100"}]}).encode()
            mock_get.return_value = resp3
            p3 = fetch_clob_orderbook(client, store, "TOKEN")
            assert p3.exists()

def test_polymarket_parse():
    evs = parse_events('[{"id": "1", "markets": [{"question": "Q"}]}]')
    assert len(evs) == 1
    
    evs_dict = parse_events('{"data": [{"id": "1", "markets": [{"tokens": ["yes", "no"]}]}]}')
    assert len(evs_dict) == 1
    
    ob = parse_clob_orderbook('{"bids": [{"price": "0.4", "size": "100"}], "asks": [{"price": "0.6", "size": "100"}]}')
    assert ob.best_bid == 0.4
