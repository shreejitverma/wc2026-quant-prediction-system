"""Phase 1 live fetch smoke test.

NOT part of the standard test suite (requires network). Run manually:
  uv run python scripts/phase1_fetch_smoke.py

Fetches one payload from each live source, stores it, parses it,
and reports what it found. This is how you verify the fetch layer on real data.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from wc2026.ingest.base import HTTPClient, RawStore, today_utc
from wc2026.ingest.elo import fetch_elo, parse_elo
from wc2026.ingest.kalshi import (
    fetch_market_detail,
    fetch_series_markets,
    parse_market_detail,
    parse_market_list,
    parse_orderbook,
)
from wc2026.ingest.kalshi import fetch_orderbook as fetch_kalshi_book
from wc2026.ingest.polymarket import fetch_wc_events, parse_events
from wc2026.ingest.results import fetch_results, parse_results


def _ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        store = RawStore(Path(d) / "raw")
        dt = today_utc()

        with HTTPClient(store, min_request_interval=2.0) as client:

            # --- Tier 1: martj42 results ---
            print("\n--- martj42 results ---")
            fetch_results(client, store, dt)
            results = parse_results(store.read_text("results_international", "results.csv", dt))
            wc_matches = [r for r in results if "World Cup" in r.tournament]
            _ok(f"{len(results):,} total match records; {len(wc_matches):,} World Cup matches")
            if results:
                latest = max(r.match_date for r in results if r.home_score is not None)
                _ok(f"latest result: {latest}")

            # --- Tier 1: eloratings.net ---
            print("\n--- eloratings.net Elo ---")
            fetch_elo(client, store, dt)
            ratings = parse_elo(store.read_text("elo_ratings", "world.tsv", dt))
            _ok(f"{len(ratings)} teams in Elo file")
            if ratings:
                top3 = ratings[:3]
                for r in top3:
                    print(f"  #{r.rank} {r.team_code} Elo={r.elo}")

            # --- Tier 3: Kalshi ---
            print("\n--- Kalshi ---")
            # Fetch markets for one series to confirm access
            p = fetch_series_markets(client, store, "KXWCADVANCE", dt)
            markets = parse_market_list(store.read_text("kalshi", "markets_KXWCADVANCE.json", dt))
            _ok(f"KXWCADVANCE: {len(markets)} markets found")
            if markets:
                m = markets[0]
                print(f"  {m.ticker} | ask={m.yes_ask} bid={m.yes_bid} vol={m.volume_24h:.0f}")

                # Fetch full detail (includes rules_primary)
                fetch_market_detail(client, store, m.ticker, dt)
                detail = parse_market_detail(
                    store.read_text("kalshi", f"market_{m.ticker}.json", dt)
                )
                n = len(detail.rules_primary)
                _ok(f"rules_primary ({n} chars): {detail.rules_primary[:80]}")

                # Fetch orderbook
                fetch_kalshi_book(client, store, m.ticker, dt)
                # Find the book file (timestamp-suffixed)
                book_files = list((store._dir("kalshi", dt)).glob(f"book_{m.ticker}_*.json"))
                if book_files:
                    ob = parse_orderbook(book_files[0].read_bytes(), ticker=m.ticker)
                    _ok(f"orderbook mid={ob.mid} bid={ob.yes_best_bid} ask={ob.yes_best_ask}")
                else:
                    _warn("no orderbook file found")

            # --- Tier 3: Polymarket ---
            print("\n--- Polymarket ---")
            paths = fetch_wc_events(client, store, dt, limit=20)
            all_events = []
            for kw, p in paths.items():
                events = parse_events(store.read_text("polymarket", p.name, dt))
                wc_events = [e for e in events if any(
                    x in e.title.lower() for x in ("world cup", "fifa", "soccer")
                )]
                if wc_events:
                    _ok(f"Keyword '{kw}': {len(wc_events)} WC events found")
                    for ev in wc_events[:2]:
                        print(f"  {ev.title[:70]} ({len(ev.markets)} markets)")
                    all_events.extend(wc_events)
            if not all_events:
                _warn("No WC2026 Polymarket events found via keyword search. "
                      "Add known slugs to configs/polymarket_slugs.yaml.")

    print("\nPhase 1 smoke test: COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
