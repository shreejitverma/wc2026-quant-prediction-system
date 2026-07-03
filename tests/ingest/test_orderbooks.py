import requests_mock

from wc2026.ingest.orderbooks import OrderbookClient


def test_orderbook_client_mock():
    client = OrderbookClient(use_mock=True)
    k_l2 = client.fetch_kalshi_l2("TEST")
    assert k_l2["yes_bid"] > 0
    p_l2 = client.fetch_polymarket_l2("TEST")
    assert p_l2["yes_bid"] > 0

def test_orderbook_client_real():
    client = OrderbookClient(use_mock=False)
    with requests_mock.Mocker() as m:
        m.get("https://trading-api.kalshi.com/trade-api/v2/markets/TICKER/orderbook", json={"orderbook": {"yes": [[45, 100]], "no": [[53, 100]]}})
        k = client.fetch_kalshi_l2("TICKER")
        assert k["yes_bid"] == 0.45
        assert k["no_bid"] == 0.53
        assert k["yes_ask"] == 0.47
        assert k["no_ask"] == 0.55
        
        # 401 fallback
        m.get("https://trading-api.kalshi.com/trade-api/v2/markets/FAIL/orderbook", status_code=401)
        k_fail = client.fetch_kalshi_l2("FAIL")
        assert k_fail["yes_bid"] == 0.45 # mock fallback
        
        # 500 fallback
        m.get("https://trading-api.kalshi.com/trade-api/v2/markets/ERR/orderbook", status_code=500)
        k_err = client.fetch_kalshi_l2("ERR")
        assert k_err["yes_ask"] == 1.0
        
        m.get("https://gamma-api.polymarket.com/markets/TOKEN", json={"bestBid": 0.4, "bestAsk": 0.6})
        p = client.fetch_polymarket_l2("TOKEN")
        assert p["yes_bid"] == 0.4
        assert p["yes_ask"] == 0.6
        
        # 404 fallback
        m.get("https://gamma-api.polymarket.com/markets/FAIL", status_code=404)
        p_fail = client.fetch_polymarket_l2("FAIL")
        assert p_fail["yes_ask"] == 1.0
        
        # 500 fallback
        m.get("https://gamma-api.polymarket.com/markets/ERR", status_code=500)
        p_err = client.fetch_polymarket_l2("ERR")
        assert p_err["yes_ask"] == 1.0
