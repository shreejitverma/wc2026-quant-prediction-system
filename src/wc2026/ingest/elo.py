"""Tier 1: World Football Elo ratings (eloratings.net).

Source: https://www.eloratings.net/World.tsv
  Tab-separated, no header, current world rankings by Elo.
  Updated roughly weekly; column layout confirmed from probe (2026-07-01):
    col 0  rank (current)
    col 1  prev_rank (previous ranking)
    col 2  team_code  (2-3 letter; AR, ES, FR, EN, BR, ...)
    col 3  elo (current rating, integer)
    col 4  region (1=UEFA/CONMEBOL, 2=CONCACAF, etc. — exact coding unconfirmed)
    col 5  elo_max (all-time highest Elo)
    col 6  elo_max_rank (rank when at elo_max)
    col 7  elo_max_year
    col 8  elo_min_rank
    col 9  elo_min (all-time lowest Elo)
    cols 10+ : change columns in pairs (rank_delta, elo_delta) for 1w/1m/3m/6m/1y/5y

Why Elo over FIFA rankings: the comparative literature (Hvattum & Arntzen 2010
"Using ELO ratings for match result prediction in association football")
demonstrates Elo-family ratings materially outperform FIFA's points formula as
match predictors. FIFA rankings use a decay-weighted points accumulation that
underweights match outcome margins and overweights confederation adjustments.
Elo self-corrects via the paired Bayesian update; FIFA points do not.

The two 3-letter code systems (Elo uses ISO-like 2-letter vs our internal IDs)
are reconciled through the crosswalk module.

Data contract: docs/data_contracts/elo_ratings.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .base import HTTPClient, RawStore, today_utc

_SOURCE = "elo_ratings"
_URL = "https://www.eloratings.net/World.tsv"
_NAME = "world.tsv"
_UA_NOTE = "research scraping; see docs/data_contracts/elo_ratings.md"

# Column indices confirmed from live probe 2026-07-01.
_COL_RANK = 0
_COL_PREV_RANK = 1
_COL_CODE = 2
_COL_ELO = 3
_COL_REGION = 4
_COL_ELO_MAX = 5
_COL_ELO_MAX_RANK = 6
_COL_ELO_MAX_YEAR = 7
_COL_ELO_MIN_RANK = 8
_COL_ELO_MIN = 9
# Change pairs start at col 10: (rank_delta_1w, elo_delta_1w, rank_1m, elo_1m, ...)
_CHANGE_PERIODS = ["1w", "1m", "3m", "6m", "1y", "5y"]


@dataclass(frozen=True)
class EloRating:
    team_code: str  # 2-3 letter code as used by eloratings.net (e.g. AR, ES, EN)
    rank: int
    prev_rank: int
    elo: int
    region: int
    elo_max: int
    elo_max_year: int
    elo_min: int
    # Change over trailing periods (may be None if column absent)
    elo_delta_1w: int | None
    elo_delta_1m: int | None
    elo_delta_3m: int | None
    elo_delta_6m: int | None
    elo_delta_1y: int | None
    elo_delta_5y: int | None

    @property
    def rank_delta(self) -> int:
        return self.prev_rank - self.rank  # positive = moved up


def fetch_elo(
    client: HTTPClient,
    store: RawStore,
    dt: datetime | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    return client.fetch(_URL, _SOURCE, _NAME, dt=dt or today_utc(), overwrite=overwrite)


def _int_or_none(s: str) -> int | None:
    """Parse a TSV value that may be '+12', '-3', or empty/non-numeric."""
    s = s.strip().replace("+", "").replace("−", "-").replace("−", "-")
    try:
        return int(s)
    except ValueError:
        return None


def parse_elo(tsv_text: str) -> list[EloRating]:
    """Parse the eloratings.net World.tsv into EloRating records.

    Pure function, no I/O. Each line is one team.
    """
    out: list[EloRating] = []
    for line in tsv_text.splitlines():
        cols = line.split("\t")
        if len(cols) < 10:
            continue
        try:
            rank = int(cols[_COL_RANK])
            prev_rank = int(cols[_COL_PREV_RANK])
            code = cols[_COL_CODE].strip()
            elo = int(cols[_COL_ELO])
            region = int(cols[_COL_REGION]) if cols[_COL_REGION].strip().isdigit() else 0
            elo_max = int(cols[_COL_ELO_MAX]) if _int_or_none(cols[_COL_ELO_MAX]) else elo
            elo_max_year = _int_or_none(cols[_COL_ELO_MAX_YEAR]) or 0
            elo_min = int(cols[_COL_ELO_MIN]) if _int_or_none(cols[_COL_ELO_MIN]) else elo
        except (ValueError, IndexError):
            continue

        # Change pairs at cols 10+; layout: rank_delta, elo_delta per period
        deltas: list[int | None] = []
        for i in range(len(_CHANGE_PERIODS)):
            elo_col = 10 + 2 * i + 1
            deltas.append(_int_or_none(cols[elo_col]) if elo_col < len(cols) else None)

        out.append(
            EloRating(
                team_code=code,
                rank=rank,
                prev_rank=prev_rank,
                elo=elo,
                region=region,
                elo_max=elo_max,
                elo_max_year=elo_max_year,
                elo_min=elo_min,
                elo_delta_1w=deltas[0] if len(deltas) > 0 else None,
                elo_delta_1m=deltas[1] if len(deltas) > 1 else None,
                elo_delta_3m=deltas[2] if len(deltas) > 2 else None,
                elo_delta_6m=deltas[3] if len(deltas) > 3 else None,
                elo_delta_1y=deltas[4] if len(deltas) > 4 else None,
                elo_delta_5y=deltas[5] if len(deltas) > 5 else None,
            )
        )
    return out


def load_elo(store: RawStore, dt: datetime | None = None) -> list[EloRating]:
    dt_key = dt or today_utc()
    return parse_elo(store.read_text(_SOURCE, _NAME, dt_key))
