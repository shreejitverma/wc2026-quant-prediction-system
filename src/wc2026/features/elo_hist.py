"""Historical Elo reconstruction from the international results timeline.

WHY this is not the same as the fetched eloratings.net snapshot:
  The current Elo file gives today's ratings. Using it to predict a match played
  in 2018 is the canonical look-ahead bias for rating models: the 2018 ratings
  implicitly include 8 years of results the model should not have seen.
  We reconstruct Elo from scratch from the martj42 results history so that
  `elo_as_of(team, dt)` returns the Elo value that was knowable just after
  the last match before `dt`.

The algorithm (standard World Football Elo variant):
  expected_a = 1 / (1 + 10^((elo_b - elo_a) / 400))
  actual_a = 1.0 (home win) / 0.5 (draw) / 0.0 (away win)
  k = K-factor (see below)
  elo_a += k * (actual_a - expected_a)
  elo_b -= k * (actual_a - expected_a)

K-factors (calibrated to international football):
  k=60  for FIFA World Cup matches
  k=50  for continental championship matches (Euros, Copa, etc.)
  k=40  for qualifiers and Nations League
  k=20  for friendlies

These K-values match eloratings.net's stated methodology. The exact values
matter less than consistency: they are tunable parameters in Phase 3, where
we will search over K by minimizing out-of-sample log-loss.

Starting ratings: teams with no history start at 1300 (average international
quality). Top programs historically converge within 30–40 matches regardless
of starting value (the "burn-in" problem is manageable for teams with long
histories).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..ingest.results import MatchResult

_DEFAULT_START_ELO = 1300.0

# K-factors by tournament type (keyword matching against tournament string)
_K_RULES: list[tuple[str, float]] = [
    ("World Cup", 60.0),
    ("continental championship", 50.0),
    ("Copa America", 50.0),
    ("UEFA Euro", 50.0),
    ("Gold Cup", 50.0),
    ("Africa Cup", 50.0),
    ("Asian Cup", 50.0),
    ("Nations League", 40.0),
    ("Qualifier", 40.0),
    ("qualification", 40.0),
    ("Friendly", 20.0),
]
_K_DEFAULT = 30.0  # anything else (e.g. "Confederations Cup")


def _k_factor(tournament: str) -> float:
    t = tournament.lower()
    for keyword, k in _K_RULES:
        if keyword.lower() in t:
            return k
    return _K_DEFAULT


def _expected(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


@dataclass
class EloState:
    """Mutable Elo state for one team at a point in time."""

    team: str
    elo: float
    last_match_date: date | None = None
    n_matches: int = 0

    def update(self, actual: float, expected: float, k: float) -> None:
        self.elo += k * (actual - expected)
        self.n_matches += 1

    @property
    def is_reliable(self) -> bool:
        """True once the team has enough matches for the burn-in to be small."""
        return self.n_matches >= 30


@dataclass
class EloTimeline:
    """Full history of Elo values for all teams, point-in-time correct.

    After `build()`, use:
      `elo_as_of(team, dt)` -> float (rating knowable just before `dt`)
      `snapshot(dt)` -> dict[team, float] (all team ratings as of `dt`)
    """

    _history: dict[str, list[tuple[date, float]]] = field(
        default_factory=dict, repr=False
    )
    _current: dict[str, float] = field(default_factory=dict, repr=False)

    def elo_as_of(self, team: str, dt: date | datetime) -> float | None:
        """The Elo rating for `team` knowable just *after* any match on `dt`.

        Returns None if the team has no history at all before `dt`.
        For a pre-match prediction on date D, use `elo_as_of(team, D - 1 day)`
        or equivalently the rating after the last match before D.
        """
        if isinstance(dt, datetime):
            dt = dt.date() if dt.tzinfo is None else dt.astimezone(UTC).date()
        hist = self._history.get(team)
        if not hist:
            return None
        # Binary search for latest entry with match_date <= dt
        lo, hi = 0, len(hist) - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if hist[mid][0] <= dt:
                result = hist[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return result

    def snapshot(self, dt: date | datetime) -> dict[str, float]:
        """All team Elo ratings as of `dt`."""
        return {
            team: self.elo_as_of(team, dt)
            for team in self._history
            if self.elo_as_of(team, dt) is not None
        }

    def all_teams(self) -> list[str]:
        return sorted(self._history.keys())

    def n_matches_for(self, team: str) -> int:
        return len(self._history.get(team, []))


def build_elo_timeline(
    results: list[MatchResult],
    *,
    start_elo: float = _DEFAULT_START_ELO,
    home_advantage: float = 100.0,
) -> EloTimeline:
    """Reconstruct the full historical Elo timeline from a sorted results list.

    `results` must be sorted by match_date ascending (oldest first).
    `home_advantage` is added to the home team's effective Elo for the
    expected-goal calculation on non-neutral venues. 100 points is the
    eloratings.net default for international football.

    The returned EloTimeline is point-in-time correct: `elo_as_of(team, D)`
    returns the rating knowable after all matches on date D have been played.
    """
    current: dict[str, float] = {}
    # history[team] = [(match_date, elo_after_match), ...]  sorted asc
    history: dict[str, list[tuple[date, float]]] = {}

    # Sort in place by match date
    sorted_results = sorted(
        (r for r in results if r.home_score is not None and r.away_score is not None),
        key=lambda r: r.match_date,
    )

    for match in sorted_results:
        home = match.home_team
        away = match.away_team
        elo_h = current.get(home, start_elo)
        elo_a = current.get(away, start_elo)

        # Home advantage on non-neutral venues
        ha = 0.0 if match.neutral else home_advantage

        exp_h = _expected(elo_h + ha, elo_a)
        exp_a = 1.0 - exp_h

        # Actual outcome (home perspective)
        if match.home_score > match.away_score:
            act_h, act_a = 1.0, 0.0
        elif match.home_score < match.away_score:
            act_h, act_a = 0.0, 1.0
        else:
            act_h, act_a = 0.5, 0.5

        k = _k_factor(match.tournament)

        elo_h_new = elo_h + k * (act_h - exp_h)
        elo_a_new = elo_a + k * (act_a - exp_a)

        current[home] = elo_h_new
        current[away] = elo_a_new

        # Record the post-match rating
        if home not in history:
            history[home] = []
        if away not in history:
            history[away] = []
        history[home].append((match.match_date, elo_h_new))
        history[away].append((match.match_date, elo_a_new))

    tl = EloTimeline(_history=history, _current=current)
    return tl


def elo_features_for_match(
    match: MatchResult,
    timeline: EloTimeline,
) -> dict[str, float | None]:
    """Extract Elo-derived features for a match, using only pre-match information.

    knowable_at for these features = match.match_date - 1 day (the rating
    knowable before the match started, after all prior matches are processed).
    """
    from datetime import timedelta

    cutoff = match.match_date - timedelta(days=1)
    elo_h = timeline.elo_as_of(match.home_team, cutoff)
    elo_a = timeline.elo_as_of(match.away_team, cutoff)

    result: dict[str, float | None] = {
        "elo_home": elo_h,
        "elo_away": elo_a,
        "elo_diff": (elo_h - elo_a) if (elo_h and elo_a) else None,
        "elo_home_is_reliable": float(timeline.n_matches_for(match.home_team) >= 30),
        "elo_away_is_reliable": float(timeline.n_matches_for(match.away_team) >= 30),
    }
    return result
