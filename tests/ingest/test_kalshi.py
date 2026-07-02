"""Tests for kalshi.py - all hermetic."""

from pathlib import Path

import pytest

from wc2026.ingest.kalshi import (
    KalshiOrderbook,
    parse_market_detail,
    parse_market_list,
    parse_orderbook,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_market_detail_fields():
    raw = (FIXTURES / "kalshi_market.json").read_text()
    mkt = parse_market_detail(raw)
    assert mkt.ticker == "KXWCADVANCE-26JUL05MEXENG-MEX"
    assert mkt.status == "active"
    assert mkt.yes_ask == pytest.approx(0.49)
    assert mkt.yes_bid == pytest.approx(0.48)
    assert mkt.no_ask == pytest.approx(0.52)
    assert mkt.no_bid == pytest.approx(0.51)


def test_implied_yes_prob():
    raw = (FIXTURES / "kalshi_market.json").read_text()
    mkt = parse_market_detail(raw)
    prob = mkt.implied_yes_prob
    assert prob is not None
    assert 0.45 < prob < 0.55  # Mexico/England fixture is near-even


def test_rules_primary_present():
    """Settlement text must be present - the contract mapper gate depends on it."""
    raw = (FIXTURES / "kalshi_market.json").read_text()
    mkt = parse_market_detail(raw)
    assert len(mkt.rules_primary) > 20
    assert "Mexico" in mkt.rules_primary or "advance" in mkt.rules_primary.lower()


def test_parse_market_list_handles_empty():
    raw = '{"markets": []}'
    assert parse_market_list(raw) == []


def test_parse_orderbook_levels():
    raw = (FIXTURES / "kalshi_orderbook.json").read_text()
    ob = parse_orderbook(raw, ticker="KXWCADVANCE-26JUL05MEXENG-MEX")
    assert isinstance(ob, KalshiOrderbook)
    # YES bids: ascending price
    assert ob.yes_bids[0].price < ob.yes_bids[-1].price
    # NO bids: ascending price
    assert ob.no_bids[0].price < ob.no_bids[-1].price


def test_orderbook_best_quotes():
    raw = (FIXTURES / "kalshi_orderbook.json").read_text()
    ob = parse_orderbook(raw, ticker="TEST")
    # Best YES bid = highest YES bid price = 0.48
    assert ob.yes_best_bid == pytest.approx(0.48)
    # Best YES ask = 1 - best NO bid = 1 - 0.51 = 0.49
    assert ob.yes_best_ask == pytest.approx(0.49)
    # Mid = (0.48 + 0.49) / 2 = 0.485
    assert ob.mid == pytest.approx(0.485, abs=0.001)


def test_orderbook_no_arbitrage_condition():
    """Best YES bid must be < best YES ask (no negative spread)."""
    raw = (FIXTURES / "kalshi_orderbook.json").read_text()
    ob = parse_orderbook(raw, ticker="TEST")
    assert ob.yes_best_bid < ob.yes_best_ask


def test_parse_market_list_from_series_json():
    """Simulate a series-markets JSON (list form)."""
    import json

    data = {
        "markets": [
            {
                "ticker": "KXWCADVANCE-26JUL05MEXENG-MEX",
                "status": "active",
                "yes_ask_dollars": "0.4900",
                "yes_bid_dollars": "0.4800",
            },
            {
                "ticker": "KXWCADVANCE-26JUL05MEXENG-ENG",
                "status": "active",
                "yes_ask_dollars": "0.5200",
                "yes_bid_dollars": "0.5100",
            },
        ]
    }
    markets = parse_market_list(json.dumps(data))
    assert len(markets) == 2
    assert markets[0].ticker == "KXWCADVANCE-26JUL05MEXENG-MEX"
    assert markets[1].yes_ask == pytest.approx(0.52)
