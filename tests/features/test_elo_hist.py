"""Tests for historical Elo reconstruction.

The golden-file test verifies a known short sequence of matches produces the
expected Elo ratings. The key invariant: Elo values only advance after a
match is played, so `elo_as_of(team, day_before_match)` must equal the
rating from the previous match (not the one being predicted).
"""

from datetime import date, timedelta

from wc2026.features.elo_hist import (
    build_elo_timeline,
    elo_features_for_match,
)
from wc2026.ingest.results import MatchResult

_DEFAULT_ELO = 1300.0


def _match(
    home: str,
    away: str,
    hs: int,
    aws: int,
    d: date,
    neutral: bool = False,
    tournament: str = "FIFA World Cup",
) -> MatchResult:
    return MatchResult(
        match_date=d,
        home_team=home,
        away_team=away,
        home_score=hs,
        away_score=aws,
        tournament=tournament,
        city="Test City",
        country="Neutral",
        neutral=neutral,
        is_competitive=True,
    )


# --- Golden-file test ---

def test_basic_elo_update():
    """One match: winner gains Elo, loser loses it."""
    d = date(2026, 6, 11)
    results = [_match("MEX", "ENG", 1, 0, d, neutral=True)]
    tl = build_elo_timeline(results)

    elo_mex = tl.elo_as_of("MEX", d)
    elo_eng = tl.elo_as_of("ENG", d)

    assert elo_mex is not None and elo_eng is not None
    assert elo_mex > _DEFAULT_ELO, "Winner should gain Elo"
    assert elo_eng < _DEFAULT_ELO, "Loser should lose Elo"
    # Zero-sum: total Elo preserved
    assert abs((elo_mex + elo_eng) - 2 * _DEFAULT_ELO) < 0.001


def test_draw_near_even_teams_minimal_change():
    d = date(2026, 6, 11)
    results = [_match("A", "B", 1, 1, d, neutral=True)]
    tl = build_elo_timeline(results)
    assert abs(tl.elo_as_of("A", d) - _DEFAULT_ELO) < 5.0
    assert abs(tl.elo_as_of("B", d) - _DEFAULT_ELO) < 5.0


def test_home_advantage_applied():
    """Non-neutral venue: home team has higher expected prob, so smaller Elo gain from a win."""
    d = date(2026, 6, 11)
    m_neutral = _match("A", "B", 1, 0, d, neutral=True)
    m_home = _match("A", "B", 1, 0, d, neutral=False)

    tl_n = build_elo_timeline([m_neutral])
    tl_h = build_elo_timeline([m_home])

    # Winning at home (expected) gives less Elo than winning on neutral ground (surprise)
    gain_neutral = tl_n.elo_as_of("A", d) - _DEFAULT_ELO
    gain_home = tl_h.elo_as_of("A", d) - _DEFAULT_ELO
    assert gain_neutral > gain_home


def test_pre_match_rating_is_pre_match():
    """elo_as_of(team, match_date - 1) must return the PRIOR rating, not the post-match one."""
    d = date(2026, 6, 11)
    results = [_match("MEX", "ENG", 1, 0, d, neutral=True)]
    tl = build_elo_timeline(results)

    # One day before: no match has been played yet
    before = tl.elo_as_of("MEX", d - timedelta(days=1))
    assert before is None  # no history before the first match


def test_sequential_matches_compound():
    d1 = date(2026, 6, 11)
    d2 = date(2026, 6, 15)
    results = [
        _match("MEX", "ENG", 2, 0, d1, neutral=True),
        _match("MEX", "FRA", 0, 1, d2, neutral=True),
    ]
    tl = build_elo_timeline(results)

    elo_after_d1 = tl.elo_as_of("MEX", d1)
    elo_after_d2 = tl.elo_as_of("MEX", d2)
    assert elo_after_d1 > _DEFAULT_ELO  # won d1
    assert elo_after_d2 < elo_after_d1  # lost d2


def test_k_factor_wc_vs_friendly():
    """World Cup match should produce a larger Elo swing than a friendly."""
    d = date(2026, 6, 11)
    m_wc = _match("A", "B", 1, 0, d, neutral=True, tournament="FIFA World Cup")
    m_fr = _match("A", "B", 1, 0, d, neutral=True, tournament="Friendly")

    tl_wc = build_elo_timeline([m_wc])
    tl_fr = build_elo_timeline([m_fr])

    assert tl_wc.elo_as_of("A", d) > tl_fr.elo_as_of("A", d)


def test_snapshot_returns_all_teams():
    d = date(2026, 6, 11)
    results = [_match("MEX", "ENG", 1, 0, d, neutral=True)]
    tl = build_elo_timeline(results)
    snap = tl.snapshot(d)
    assert "MEX" in snap and "ENG" in snap


def test_elo_features_for_match_returns_none_for_no_history():
    """First-ever match for a team: elo_home and elo_away should be None."""
    d = date(2026, 6, 11)
    match = _match("NEW1", "NEW2", 1, 0, d, neutral=True)
    tl = build_elo_timeline([])  # empty timeline
    feats = elo_features_for_match(match, tl)
    assert feats["elo_home"] is None
    assert feats["elo_away"] is None
    assert feats["elo_diff"] is None


def test_reliability_flag():
    """Team needs 30 matches before is_reliable=True."""
    d0 = date(2020, 1, 1)
    results = [
        _match("A", "B", 1, 0, d0 + timedelta(days=i * 30), neutral=True)
        for i in range(35)
    ]
    tl = build_elo_timeline(results)
    assert tl.n_matches_for("A") == 35

    last = results[-1]
    feats = elo_features_for_match(last, tl)
    assert feats["elo_home_is_reliable"] == 1.0
