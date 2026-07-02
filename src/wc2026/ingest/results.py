"""Tier 1: International football results (martj42 / GitHub).

Source: https://github.com/martj42/international_results
  File: results.csv (full history since 1872; updated after every match day)

Fetch/parse separation:
  fetch_results(client, store, dt)  -> Path  (idempotent)
  parse_results(csv_text)           -> list[MatchResult]  (pure, fixture-testable)

Leakage notes:
  - `knowable_at` = the fetch timestamp (conservative; suits training cutoffs).
  - Results can be retroactively corrected (score adjustments, walkovers). The
    raw file is dated, so we always know *which version* we trained on.
  - `home_score` / `away_score` are null for scheduled future matches - never
    use them as features without checking nullability.

Data contract: docs/data_contracts/results_international.md
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .base import HTTPClient, RawStore, today_utc

_SOURCE = "results_international"
_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
_NAME = "results.csv"

# Tournament strings that indicate a competitive (non-friendly) match.
# Used as a feature flag; we never drop friendlies from the raw store.
_COMPETITIVE_KEYWORDS = (
    "FIFA",
    "World Cup",
    "UEFA",
    "CONMEBOL",
    "CONCACAF",
    "CAF",
    "AFC",
    "OFC",
    "Copa",
    "Euro",
    "Gold Cup",
    "Nations League",
    "Confederation",
    "Olympic",
)


@dataclass(frozen=True)
class MatchResult:
    match_date: date
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    tournament: str
    city: str
    country: str
    neutral: bool
    is_competitive: bool  # derived; not in source

    @property
    def result(self) -> str | None:
        """'H' / 'D' / 'A' / None for unplayed."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "H"
        if self.away_score > self.home_score:
            return "A"
        return "D"


def fetch_results(
    client: HTTPClient,
    store: RawStore,
    dt: datetime | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Fetch the full international results CSV (idempotent: no-op if already fetched today)."""
    return client.fetch(_URL, _SOURCE, _NAME, dt=dt or today_utc(), overwrite=overwrite)


def parse_results(csv_text: str) -> list[MatchResult]:
    """Parse the martj42 CSV into a list of MatchResult dataclasses.

    Pure function: no I/O, no side effects. Suitable for fixture-based testing.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    out: list[MatchResult] = []
    for row in reader:
        try:
            match_date = date.fromisoformat(row["date"])
            hs = row["home_score"].strip()
            aws = row["away_score"].strip()
            home_score = int(hs) if hs else None
            away_score = int(aws) if aws else None
            neutral = row["neutral"].strip().upper() in ("TRUE", "1", "YES")
            tournament = row["tournament"].strip()
            is_competitive = any(k in tournament for k in _COMPETITIVE_KEYWORDS)
            out.append(
                MatchResult(
                    match_date=match_date,
                    home_team=row["home_team"].strip(),
                    away_team=row["away_team"].strip(),
                    home_score=home_score,
                    away_score=away_score,
                    tournament=tournament,
                    city=row.get("city", "").strip(),
                    country=row.get("country", "").strip(),
                    neutral=neutral,
                    is_competitive=is_competitive,
                )
            )
        except (KeyError, ValueError):
            continue  # malformed row; skip and continue
    return out


def load_results(store: RawStore, dt: datetime | None = None) -> list[MatchResult]:
    """Read the raw CSV from store and parse it (convenience wrapper)."""
    dt_key = dt or today_utc()
    text = store.read_text(_SOURCE, _NAME, dt_key)
    return parse_results(text)
