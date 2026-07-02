"""Tests for polymarket.py - all hermetic."""

from pathlib import Path

import pytest

from wc2026.ingest.polymarket import (
    PolyOrderbook,
    parse_clob_orderbook,
    parse_events,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_events_count():
    raw = (FIXTURES / "polymarket_events.json").read_text()
    events = parse_events(raw)
    assert len(events) == 1
    assert events[0].title == "FIFA World Cup 2026 Winner"


def test_parse_events_markets():
    raw = (FIXTURES / "polymarket_events.json").read_text()
    events = parse_events(raw)
    markets = events[0].markets
    assert len(markets) == 2
    assert markets[0].question.startswith("Will Argentina")
    assert markets[0].liquidity == pytest.approx(45230.50)


def test_parse_events_token_ids():
    raw = (FIXTURES / "polymarket_events.json").read_text()
    events = parse_events(raw)
    m = events[0].markets[0]
    assert m.token_id_yes == "0xtoken_yes_001"
    assert m.token_id_no == "0xtoken_no_001"


def test_parse_events_resolution_source():
    """Settlement text must survive parsing - needed by contract mapper (Phase 5)."""
    raw = (FIXTURES / "polymarket_events.json").read_text()
    events = parse_events(raw)
    for mkt in events[0].markets:
        assert len(mkt.resolution_source) > 0


def test_parse_clob_orderbook_quotes():
    raw = (FIXTURES / "polymarket_clob.json").read_text()
    ob = parse_clob_orderbook(raw, condition_id="0xabc123", token_id="0xtoken_yes_001")
    assert isinstance(ob, PolyOrderbook)
    assert ob.best_bid == pytest.approx(0.32)
    assert ob.best_ask == pytest.approx(0.34)
    assert ob.mid == pytest.approx(0.33)


def test_clob_bid_ask_ordering():
    raw = (FIXTURES / "polymarket_clob.json").read_text()
    ob = parse_clob_orderbook(raw)
    # Bids descending
    prices = [b.price for b in ob.bids]
    assert prices == sorted(prices, reverse=True)
    # Asks ascending
    prices_a = [a.price for a in ob.asks]
    assert prices_a == sorted(prices_a)


def test_clob_no_arbitrage():
    raw = (FIXTURES / "polymarket_clob.json").read_text()
    ob = parse_clob_orderbook(raw)
    assert ob.best_bid < ob.best_ask


def test_parse_events_empty_list():
    events = parse_events("[]")
    assert events == []
