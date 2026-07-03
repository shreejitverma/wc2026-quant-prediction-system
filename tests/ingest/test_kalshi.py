import json
import tempfile
from unittest.mock import MagicMock, patch

from wc2026.ingest.base import HTTPClient, RawStore
from wc2026.ingest.kalshi import (
    fetch_all_wc_markets,
    fetch_market_detail,
    fetch_orderbook,
    fetch_series_markets,
    parse_market_detail,
    parse_market_list,
    parse_orderbook,
)


@patch('httpx.Client.get')
def test_kalshi_fetch(mock_get):
    with tempfile.TemporaryDirectory() as td:
        store = RawStore(td)
        with HTTPClient(store, min_request_interval=0.0) as client:
            # fetch_series_markets
            resp1 = MagicMock()
            resp1.status_code = 200
            resp1.content = json.dumps({"markets": [{"ticker": "A"}], "cursor": None}).encode()
            mock_get.return_value = resp1
            p = fetch_series_markets(client, store, "KXWCADVANCE")
            assert p.exists()
            
            # detail
            resp2 = MagicMock()
            resp2.status_code = 200
            resp2.content = json.dumps({"market": {"ticker": "TICKER"}}).encode()
            mock_get.return_value = resp2
            p2 = fetch_market_detail(client, store, "TICKER")
            assert p2.exists()
            
            # orderbook
            resp3 = MagicMock()
            resp3.status_code = 200
            resp3.content = json.dumps({"orderbook_fp": {"yes_dollars": [["0.4", "100"]], "no_dollars": [["0.6", "100"]]}}).encode()
            mock_get.return_value = resp3
            p3 = fetch_orderbook(client, store, "TICKER")
            assert p3.exists()
            
            res = fetch_all_wc_markets(client, store, series=("KXWCADVANCE",))
            assert len(res) == 1

def test_kalshi_parse():
    ml = parse_market_list('{"markets": [{"ticker": "A", "yes_ask_dollars": "0.5", "volume_fp": "100"}]}')
    assert len(ml) == 1
    
    ml2 = parse_market_list('{"markets": [{"ticker": "A", "yes_ask_dollars": "0.5", "yes_bid_dollars": "0.4"}]}')
    assert ml2[0].implied_yes_prob == 0.45
    
    ml3 = parse_market_list('{"markets": [{"ticker": "A", "last_price_dollars": "0.45"}]}')
    assert ml3[0].implied_yes_prob == 0.45
    
    md = parse_market_detail('{"market": {"ticker": "B"}}')
    assert md.ticker == "B"
    
    ob = parse_orderbook('{"orderbook_fp": {"yes_dollars": [["0.4", "100"], ["bad"]], "no_dollars": [["0.6", "100"]]}}', "TICKER")
    assert ob.yes_best_ask == 0.4
