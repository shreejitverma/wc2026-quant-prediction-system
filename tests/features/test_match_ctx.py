"""Tests for match context features."""

from datetime import date

from wc2026.features.match_ctx import (
    VENUE_ALTITUDE_M,
    build_match_context,
    compute_rest_days,
    infer_stage,
)
from wc2026.ingest.results import MatchResult


def _match(
    home: str,
    away: str,
    d: date,
    city: str = "Los Angeles",
    tournament: str = "FIFA World Cup",
    neutral: bool = True,
    hs: int = 1,
    aws: int = 0,
) -> MatchResult:
    return MatchResult(
        match_date=d,
        home_team=home,
        away_team=away,
        home_score=hs,
        away_score=aws,
        tournament=tournament,
        city=city,
        country="USA",
        neutral=neutral,
        is_competitive=True,
    )


def test_altitude_mexico_city():
    assert VENUE_ALTITUDE_M["Mexico City"] == 2240.0


def test_altitude_la_is_low():
    assert VENUE_ALTITUDE_M.get("Los Angeles", 0) < 500


def test_infer_stage_world_cup():
    label, order = infer_stage("FIFA World Cup")
    assert label == "Group Stage"
    assert order == 0


def test_infer_stage_final():
    label, order = infer_stage("FIFA World Cup Final")
    assert label == "Final"
    assert order == 6


def test_infer_stage_quarter():
    label, order = infer_stage("FIFA World Cup Quarter-final")
    assert order == 3


def test_rest_days_basic():
    d1 = date(2026, 6, 20)
    d2 = date(2026, 6, 24)
    prior = [_match("MEX", "CAN", d1, hs=1, aws=0)]
    days = compute_rest_days("MEX", d2, prior)
    assert days == 4


def test_rest_days_no_prior():
    days = compute_rest_days("NEW", date(2026, 6, 20), [])
    assert days is None


def test_build_match_context_altitude():
    d = date(2026, 6, 11)
    match = _match("MEX", "ENG", d, city="Mexico City")
    ctx = build_match_context(match, prior_results=[])
    assert ctx.altitude_m == 2240.0
    assert ctx.to_features()["high_altitude"] == 1.0


def test_build_match_context_rest_days():
    d1 = date(2026, 6, 20)
    d2 = date(2026, 6, 24)
    prior = [_match("MEX", "CAN", d1)]
    match = _match("MEX", "ENG", d2)
    ctx = build_match_context(match, prior_results=prior)
    assert ctx.home_rest_days == 4


def test_build_match_context_knockout():
    d = date(2026, 7, 5)
    match = _match("MEX", "ENG", d, tournament="FIFA World Cup Round of 32")
    ctx = build_match_context(match, prior_results=[])
    assert ctx.is_knockout is True
    assert ctx.to_features()["is_knockout"] == 1.0


def test_build_match_context_neutral():
    d = date(2026, 6, 11)
    match = _match("MEX", "ENG", d, neutral=True)
    ctx = build_match_context(match, prior_results=[])
    assert ctx.neutral is True
    assert ctx.to_features()["neutral"] == 1.0


def test_feature_dict_has_expected_keys():
    d = date(2026, 6, 11)
    match = _match("MEX", "ENG", d)
    ctx = build_match_context(match, prior_results=[])
    feats = ctx.to_features()
    for key in ["neutral", "altitude_m", "stage_order", "is_knockout",
                "is_world_cup", "is_competitive", "dead_rubber", "high_altitude"]:
        assert key in feats, f"Missing feature: {key}"
