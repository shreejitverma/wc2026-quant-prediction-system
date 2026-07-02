"""Tier 3: Polymarket Gamma API and CLOB.

Two separate APIs:
  Gamma API   https://gamma-api.polymarket.com   metadata, market search
  CLOB API    https://clob.polymarket.com         order books (read-only, no auth)

WC2026 market discovery: Gamma's tag_slug=world-cup-2026 returns unrelated
markets (confirmed probe 2026-07-01). We use keyword search via
`/events?q={keyword}` as the primary discovery path, then slug-based lookups
for known market slugs. A persistent slug registry (configs/polymarket_slugs.yaml)
serves as a stable index that we can extend manually.

CLOB orderbook format:
  GET /book?token_id={token_id}
  Returns {asks: [{price, size}, ...], bids: [{price, size}, ...]}
  Prices are in USDC (0.0-1.0); sizes are in USDC.
  US persons are geo-restricted from trading; we use the CLOB read-only for
  price benchmarking only (ADR-0007).

Settlement risk note (ADR-0006): Polymarket uses UMA as an oracle. UMA
resolution disputes have historically taken 1-7 days and occasionally resolved
against the obvious economic outcome. This is a priced risk in our fair-value
model. DO NOT price a Polymarket contract without parsing the resolution rules
and confirming the data source (e.g. "official FIFA match records" vs "major
media consensus").

Data contract: docs/data_contracts/polymarket.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import HTTPClient, RawStore, today_utc

_SOURCE = "polymarket"
_GAMMA = "https://gamma-api.polymarket.com"
_CLOB = "https://clob.polymarket.com"

# Search keywords likely to surface WC2026 markets.
_WC_KEYWORDS: tuple[str, ...] = (
    "world cup",
    "FIFA",
    "soccer world",
    "2026 World Cup",
)


@dataclass(frozen=True)
class PolyLevel:
    price: float  # USDC (0-1)
    size: float  # USDC


@dataclass
class PolyOrderbook:
    condition_id: str
    token_id: str
    snapshot_utc: str
    bids: list[PolyLevel]  # descending price
    asks: list[PolyLevel]  # ascending price

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round((self.best_bid + self.best_ask) / 2, 4)


@dataclass
class PolyMarket:
    """A single Polymarket binary outcome market (one token_id = YES token)."""

    condition_id: str
    question_id: str
    question: str
    description: str
    slug: str
    end_date: str
    liquidity: float
    # token ids for YES and NO outcomes (from tokens list in CLOB)
    token_id_yes: str
    token_id_no: str
    resolution_source: str
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class PolyEvent:
    """A Polymarket event (one or more markets)."""

    event_id: str
    title: str
    slug: str
    markets: list[PolyMarket]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


# --- Fetch functions ---


def fetch_wc_events(
    client: HTTPClient,
    store: RawStore,
    dt: datetime | None = None,
    *,
    limit: int = 100,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Search Gamma API for WC2026 events using keyword list.

    Returns dict of {keyword: path_to_raw_json}.
    """
    dt_key = dt or today_utc()
    results: dict[str, Path] = {}
    for kw in _WC_KEYWORDS:
        name = f"events_search_{kw.replace(' ', '_')}.json"
        if not overwrite and store.exists(_SOURCE, name, dt_key):
            results[kw] = store.path(_SOURCE, name, dt_key)
            continue
        p, _ = client.fetch_json(
            f"{_GAMMA}/events",
            _SOURCE,
            name,
            dt=dt_key,
            params={"q": kw, "limit": limit},
            overwrite=overwrite,
        )
        results[kw] = p
    return results


def fetch_market_by_slug(
    client: HTTPClient,
    store: RawStore,
    slug: str,
    dt: datetime | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Fetch a specific Polymarket market by its Gamma slug."""
    dt_key = dt or today_utc()
    name = f"market_{slug}.json"
    return client.fetch(
        f"{_GAMMA}/markets",
        _SOURCE,
        name,
        dt=dt_key,
        params={"slug": slug},
        overwrite=overwrite,
    )


def fetch_clob_orderbook(
    client: HTTPClient,
    store: RawStore,
    token_id: str,
    dt: datetime | None = None,
    *,
    overwrite: bool = True,
) -> Path:
    """Fetch L2 orderbook from Polymarket CLOB for a YES token.

    CLOB books are ephemeral so overwrite=True by default.
    """
    from ..time_utils import utc_now

    dt_key = dt or today_utc()
    ts = utc_now().strftime("%H%M%S")
    name = f"clob_{token_id[:16]}_{ts}.json"
    return client.fetch(
        f"{_CLOB}/book",
        _SOURCE,
        name,
        dt=dt_key,
        params={"token_id": token_id},
        overwrite=True,
    )


# --- Parse functions (pure, fixture-testable) ---


def parse_events(json_text: str | bytes) -> list[PolyEvent]:
    """Parse a Gamma /events response into PolyEvent records.

    The Gamma response may be a list (direct) or a dict with a 'data' key.
    """
    data = json.loads(json_text)
    raw_events: list[dict[str, Any]] = data if isinstance(data, list) else data.get("data", [])
    out: list[PolyEvent] = []
    for ev in raw_events:
        markets = _parse_markets_from_event(ev.get("markets", []))
        out.append(
            PolyEvent(
                event_id=str(ev.get("id", "")),
                title=ev.get("title", ""),
                slug=ev.get("slug", ""),
                markets=markets,
                raw=ev,
            )
        )
    return out


def _parse_markets_from_event(raw_markets: list[dict[str, Any]]) -> list[PolyMarket]:
    out: list[PolyMarket] = []
    for m in raw_markets:
        tokens = m.get("tokens", []) or m.get("clobTokenIds", []) or []
        token_yes = tokens[0] if len(tokens) > 0 else ""
        token_no = tokens[1] if len(tokens) > 1 else ""
        out.append(
            PolyMarket(
                condition_id=m.get("conditionId", ""),
                question_id=m.get("questionId", ""),
                question=m.get("question", ""),
                description=m.get("description", ""),
                slug=m.get("slug", ""),
                end_date=m.get("endDate", ""),
                liquidity=float(m.get("liquidity", 0) or 0),
                token_id_yes=token_yes,
                token_id_no=token_no,
                resolution_source=m.get("resolutionSource", ""),
                raw=m,
            )
        )
    return out


def parse_clob_orderbook(
    json_text: str | bytes, *, condition_id: str = "", token_id: str = ""
) -> PolyOrderbook:
    from ..time_utils import to_iso, utc_now

    data = json.loads(json_text)
    bids = sorted(
        [PolyLevel(price=float(b["price"]), size=float(b["size"])) for b in data.get("bids", [])],
        key=lambda x: -x.price,
    )
    asks = sorted(
        [PolyLevel(price=float(a["price"]), size=float(a["size"])) for a in data.get("asks", [])],
        key=lambda x: x.price,
    )
    return PolyOrderbook(
        condition_id=condition_id,
        token_id=token_id,
        snapshot_utc=to_iso(utc_now()),
        bids=bids,
        asks=asks,
    )
