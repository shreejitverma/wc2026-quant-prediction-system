"""Tier 3: Kalshi markets, orderbooks, and event data.

Base URL: https://api.elections.kalshi.com/trade-api/v2
Public endpoints (no auth required):
  GET /markets?series_ticker={s}&limit=N&cursor={c}   -> paginated market list
  GET /markets/{ticker}                                -> individual market (full fields)
  GET /markets/{ticker}/orderbook?depth=N              -> L2 book

WC2026 series tickers confirmed live (2026-07-01):
  KXWCADVANCE    team to advance from a match
  KXWCGOAL       match goalscorer markets
  KXWCTOTAL      match total goals (over/under)
  KXWCCORNERS    corner markets
  KXWCSHOT       shots markets
  KXSOCCERBTTS   both teams to score
  KXWCGROUPBOTTOM group bottom finisher
  KXWCREGIONKO   region teams to reach knockout

Orderbook format (confirmed live):
  orderbook_fp.no_dollars  = [[price_str, cumulative_size_str], ...]
  orderbook_fp.yes_dollars = [[price_str, cumulative_size_str], ...]
  prices are in USD (e.g. "0.4900" = 49¢ = p=0.49)

Contract mapper note (Phase 5): `rules_primary` in the individual market response
is the human-readable settlement text. It MUST be parsed and matched to a model
event before pricing; see ADR-0006. Never price a contract without reading it.

Data contract: docs/data_contracts/kalshi.md

Trades endpoint (/markets/{ticker}/trades) requires authenticated session.
We do not fetch trades in this phase; it is a paid/auth upgrade point (ADR-0007).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import HTTPClient, RawStore, today_utc

_SOURCE = "kalshi"
_BASE = "https://api.elections.kalshi.com/trade-api/v2"
_PAGE_SIZE = 200

# All WC2026 series we track. Extend this list as new series launch.
WC_SERIES: tuple[str, ...] = (
    "KXWCADVANCE",
    "KXWCGOAL",
    "KXWCTOTAL",
    "KXWCCORNERS",
    "KXWCSHOT",
    "KXSOCCERBTTS",
    "KXWCGROUPBOTTOM",
    "KXWCREGIONKO",
    "KXWCGOALRECORD",
    "KXWCGOALLEADER",
    "KXWCLONGESTPEN",
    "KXWCMENTION",
    "KXWCSONG",
    "KXWC2HSPREAD",
    "KXWCSAVE",
)


@dataclass(frozen=True)
class KalshiLevel:
    price: float  # USD probability (0-1)
    size: float  # cumulative USD


@dataclass(frozen=True)
class KalshiOrderbook:
    ticker: str
    snapshot_utc: str
    yes_bids: list[KalshiLevel]  # ascending price (cheapest first)
    no_bids: list[KalshiLevel]  # ascending price on NO side
    depth: int = 10

    @property
    def yes_best_ask(self) -> float | None:
        """Best YES ask price = 1 - best NO bid (cheapest NO buy = most expensive YES sell)."""
        if not self.no_bids:
            return None
        return round(1.0 - self.no_bids[0].price, 4)

    @property
    def yes_best_bid(self) -> float | None:
        if not self.yes_bids:
            return None
        return self.yes_bids[-1].price  # highest YES bid

    @property
    def mid(self) -> float | None:
        a, b = self.yes_best_ask, self.yes_best_bid
        if a is None or b is None:
            return None
        return round((a + b) / 2, 4)


@dataclass
class KalshiMarket:
    ticker: str
    event_ticker: str
    status: str
    title: str
    subtitle: str
    yes_ask: float | None  # USD (0-1)
    yes_bid: float | None
    no_ask: float | None
    no_bid: float | None
    last_price: float | None
    volume: float
    volume_24h: float
    open_interest: float
    close_time: str
    expected_expiration: str
    rules_primary: str  # settlement text - MUST be read before pricing
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def implied_yes_prob(self) -> float | None:
        """Mid-market yes probability (from bid/ask, not last price)."""
        if self.yes_ask is not None and self.yes_bid is not None:
            return round((self.yes_ask + self.yes_bid) / 2, 4)
        if self.last_price is not None:
            return self.last_price
        return None


def _parse_market(m: dict[str, Any]) -> KalshiMarket:
    def _f(key: str) -> float | None:
        v = m.get(key)
        return float(v) if v not in (None, "", "0.0000") else None

    def _fp(key: str) -> float:
        v = m.get(key, "0")
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    return KalshiMarket(
        ticker=m.get("ticker", ""),
        event_ticker=m.get("event_ticker", ""),
        status=m.get("status", ""),
        title=m.get("title", ""),
        subtitle=m.get("subtitle", "") or m.get("no_sub_title", ""),
        yes_ask=_f("yes_ask_dollars"),
        yes_bid=_f("yes_bid_dollars"),
        no_ask=_f("no_ask_dollars"),
        no_bid=_f("no_bid_dollars"),
        last_price=_f("last_price_dollars"),
        volume=_fp("volume_fp"),
        volume_24h=_fp("volume_24h_fp"),
        open_interest=_fp("open_interest_fp"),
        close_time=m.get("close_time", ""),
        expected_expiration=m.get("expected_expiration_time", ""),
        rules_primary=m.get("rules_primary", ""),
        raw=m,
    )


def _parse_levels(raw: list[list[str]]) -> list[KalshiLevel]:
    out = []
    for item in raw:
        try:
            out.append(KalshiLevel(price=float(item[0]), size=float(item[1])))
        except (IndexError, ValueError):
            continue
    return sorted(out, key=lambda x: x.price)


# --- Fetch functions ---


def fetch_series_markets(
    client: HTTPClient,
    store: RawStore,
    series: str,
    dt: datetime | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Fetch all markets for one series (paginated), store as one JSON file per series."""
    dt_key = dt or today_utc()
    name = f"markets_{series}.json"
    if not overwrite and store.exists(_SOURCE, name, dt_key):
        return store.path(_SOURCE, name, dt_key)

    markets: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"series_ticker": series, "limit": _PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        _, data = client.fetch_json(
            f"{_BASE}/markets",
            _SOURCE,
            f"_tmp_{series}_{len(markets)}.json",
            dt=dt_key,
            params=params,
            overwrite=True,
        )
        batch = data.get("markets", [])
        markets.extend(batch)
        cursor = data.get("cursor")
        if not batch or not cursor:
            break

    store.write(
        _SOURCE,
        name,
        json.dumps({"markets": markets, "series": series}, indent=2),
        dt=dt_key,
        url=f"{_BASE}/markets?series_ticker={series}",
        overwrite=overwrite,
    )
    return store.path(_SOURCE, name, dt_key)


def fetch_market_detail(
    client: HTTPClient,
    store: RawStore,
    ticker: str,
    dt: datetime | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Fetch the full individual market record (includes rules_primary)."""
    dt_key = dt or today_utc()
    name = f"market_{ticker}.json"
    return client.fetch(
        f"{_BASE}/markets/{ticker}",
        _SOURCE,
        name,
        dt=dt_key,
        overwrite=overwrite,
    )


def fetch_orderbook(
    client: HTTPClient,
    store: RawStore,
    ticker: str,
    dt: datetime | None = None,
    *,
    depth: int = 10,
    overwrite: bool = True,  # orderbooks should always be fresh
) -> Path:
    """Fetch L2 orderbook snapshot. Always overwrites (books are ephemeral)."""
    from ..time_utils import utc_now

    dt_key = dt or today_utc()
    ts = utc_now().strftime("%H%M%S")
    return client.fetch(
        f"{_BASE}/markets/{ticker}/orderbook",
        _SOURCE,
        f"book_{ticker}_{ts}.json",
        dt=dt_key,
        params={"depth": depth},
        overwrite=True,
    )


def fetch_all_wc_markets(
    client: HTTPClient,
    store: RawStore,
    dt: datetime | None = None,
    series: tuple[str, ...] = WC_SERIES,
) -> dict[str, Path]:
    """Fetch market lists for all WC series."""
    return {s: fetch_series_markets(client, store, s, dt) for s in series}


# --- Parse functions (pure, fixture-testable) ---


def parse_market_list(json_text: str | bytes) -> list[KalshiMarket]:
    """Parse the stored series-markets JSON into KalshiMarket records."""
    data = json.loads(json_text)
    return [_parse_market(m) for m in data.get("markets", [])]


def parse_market_detail(json_text: str | bytes) -> KalshiMarket:
    """Parse an individual market JSON (the richer form with rules_primary)."""
    data = json.loads(json_text)
    return _parse_market(data.get("market", data))


def parse_orderbook(json_text: str | bytes, ticker: str = "") -> KalshiOrderbook:
    """Parse an orderbook snapshot into a KalshiOrderbook."""
    from ..time_utils import to_iso, utc_now

    data = json.loads(json_text)
    ob = data.get("orderbook_fp", data)
    return KalshiOrderbook(
        ticker=ticker,
        snapshot_utc=to_iso(utc_now()),
        yes_bids=_parse_levels(ob.get("yes_dollars", [])),
        no_bids=_parse_levels(ob.get("no_dollars", [])),
    )
