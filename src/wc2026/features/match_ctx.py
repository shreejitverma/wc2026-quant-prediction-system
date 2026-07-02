"""Match-context features: neutral venue, stage, rest days, altitude, dead-rubber.

All features here are derivable from information that is knowable *before*
kickoff. The `knowable_at` for each family:
  - neutral/stage/tournament: knowable when the fixture is scheduled (days/weeks ahead)
  - rest_days: knowable when the fixture list is published
  - altitude: knowable always (venue geography doesn't change)
  - dead_rubber: partially knowable (some group situations are resolved before the match)

2026-specific:
  - 12 groups of 4; top 2 advance + best 8 third-placed teams
  - Round of 32 (R32) not "Round of 16" — 48 teams means there's an extra round
  - Temperature/humidity effects suppress total goals in afternoon kickoffs
    (venue + kickoff time + calendar month → heat stress index)

Altitude data (static lookup): venues above 1500m get an explicit flag because
altitude affects aerobic capacity (stronger teams' style suppressed, total goals
often lower than expected from team quality alone). Mexico City (~2240m) is the
canonical example.

Rest days: short turnaround (<72h) is a documented disadvantage. Some evidence
it matters more for teams that pressed harder in the prior match, but we encode
the raw rest-day count and let the model learn the coefficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

# Static altitude lookup by city name (metres above sea level).
# Source: Wikipedia / official venue data for WC2026 host cities.
# Only cities > 500m are listed; unlisted = sea-level assumption.
VENUE_ALTITUDE_M: dict[str, float] = {
    "Mexico City": 2240.0,
    "Guadalajara": 1566.0,
    "Monterrey": 538.0,
    "Dallas": 139.0,
    "Kansas City": 265.0,
    "Los Angeles": 71.0,
    "San Francisco": 16.0,
    "New York City": 10.0,
    "Boston": 9.0,
    "Miami": 2.0,
    "Seattle": 23.0,
    "Vancouver": 70.0,
    "Toronto": 76.0,
}

# Stage identifiers (WC2026-specific)
STAGE_ORDER: dict[str, int] = {
    "Group Stage": 0,
    "Round of 32": 1,   # 48-team format: R32 before R16
    "Round of 16": 2,
    "Quarter-final": 3,
    "Semi-final": 4,
    "Third-place play-off": 5,
    "Final": 6,
}


@dataclass(frozen=True)
class MatchContext:
    match_id: str
    match_date: date
    home_team: str
    away_team: str
    neutral: bool
    tournament: str
    stage: str
    city: str
    country: str

    # Derived
    altitude_m: float
    stage_order: int
    is_knockout: bool
    is_world_cup: bool
    is_competitive: bool

    # Set externally (not derivable from match record alone)
    home_rest_days: int | None
    away_rest_days: int | None
    dead_rubber: bool  # True if both teams' qualification status is decided

    def to_features(self) -> dict[str, Any]:
        """Return a flat feature dict suitable for FeatureStore.upsert_many()."""
        return {
            "neutral": float(self.neutral),
            "altitude_m": self.altitude_m,
            "stage_order": float(self.stage_order),
            "is_knockout": float(self.is_knockout),
            "is_world_cup": float(self.is_world_cup),
            "is_competitive": float(self.is_competitive),
            "dead_rubber": float(self.dead_rubber),
            "home_rest_days": (
                float(self.home_rest_days) if self.home_rest_days is not None else None
            ),
            "away_rest_days": (
                float(self.away_rest_days) if self.away_rest_days is not None else None
            ),
            "rest_days_diff": (
                float(self.home_rest_days - self.away_rest_days)
                if (self.home_rest_days is not None and self.away_rest_days is not None)
                else None
            ),
            "high_altitude": float(self.altitude_m > 1500.0),
        }


def infer_stage(tournament: str) -> tuple[str, int]:
    """Infer stage label and order from a tournament string.

    Returns (stage_label, stage_order). Falls back to "Group Stage" if unknown.
    """
    t = tournament.lower()
    # Sort by descending label length so "Quarter-final" matches before "Final"
    for stage, order in sorted(STAGE_ORDER.items(), key=lambda x: -len(x[0])):
        if stage.lower() in t:
            return stage, order
    if "world cup" in t:
        return "Group Stage", 0
    return "Unknown", -1


def compute_rest_days(
    team: str,
    match_date: date,
    prior_results: list[Any],  # list[MatchResult]
) -> int | None:
    """Days since team's last match before match_date.

    Uses the results list to find the most recent prior match.
    Returns None if no prior match found.
    """
    prior_dates = [
        r.match_date
        for r in prior_results
        if (r.home_team == team or r.away_team == team)
        and r.match_date < match_date
        and r.home_score is not None
    ]
    if not prior_dates:
        return None
    last = max(prior_dates)
    return (match_date - last).days


def build_match_context(
    match: Any,  # MatchResult
    *,
    prior_results: list[Any],  # list[MatchResult] for rest-day computation
    dead_rubber: bool = False,
) -> MatchContext:
    """Build a MatchContext from a MatchResult plus prior history."""
    stage, stage_order = infer_stage(match.tournament)
    altitude = VENUE_ALTITUDE_M.get(match.city, 0.0)

    home_rest = compute_rest_days(match.home_team, match.match_date, prior_results)
    away_rest = compute_rest_days(match.away_team, match.match_date, prior_results)

    return MatchContext(
        match_id=_match_id(match),
        match_date=match.match_date,
        home_team=match.home_team,
        away_team=match.away_team,
        neutral=match.neutral,
        tournament=match.tournament,
        stage=stage,
        city=match.city,
        country=match.country,
        altitude_m=altitude,
        stage_order=stage_order,
        is_knockout=stage_order >= 1,
        is_world_cup="World Cup" in match.tournament,
        is_competitive=match.is_competitive,
        home_rest_days=home_rest,
        away_rest_days=away_rest,
        dead_rubber=dead_rubber,
    )


def _match_id(match: Any) -> str:
    """Canonical match identifier: HOME-AWAY-YYYYMMDD."""
    return f"{match.home_team}-{match.away_team}-{match.match_date.strftime('%Y%m%d')}"
