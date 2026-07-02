"""Tests for results.py - all hermetic (no network)."""

from datetime import date
from pathlib import Path

from wc2026.ingest.results import parse_results

FIXTURE = Path(__file__).parent / "fixtures" / "results_sample.csv"


def _load() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_basic_count():
    results = parse_results(_load())
    assert len(results) == 8


def test_parse_types_and_values():
    r = parse_results(_load())
    wc = r[0]
    assert wc.home_team == "Mexico"
    assert wc.away_team == "Qatar"
    assert wc.home_score == 2
    assert wc.away_score == 0
    assert wc.neutral is True
    assert wc.result == "H"
    assert isinstance(wc.match_date, date)


def test_competitive_flag():
    results = parse_results(_load())
    wc_match = next(r for r in results if "World Cup" in r.tournament)
    friendly = next(r for r in results if r.tournament == "Friendly")
    assert wc_match.is_competitive is True
    assert friendly.is_competitive is False


def test_draw_result():
    results = parse_results(_load())
    draw = next(r for r in results if r.home_score == r.away_score and r.home_score is not None)
    assert draw.result == "D"


def test_neutral_parsing():
    results = parse_results(_load())
    # Non-neutral: country == team's home country
    non_neutral = next(r for r in results if not r.neutral)
    assert non_neutral.neutral is False


def test_tolerates_malformed_row():
    bad_csv = "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
    bad_csv += "not-a-date,A,B,1,0,Friendly,X,Y,FALSE\n"
    bad_csv += "2026-06-11,C,D,2,1,Friendly,X,Y,FALSE\n"
    results = parse_results(bad_csv)
    # The malformed date row is skipped; the good row is parsed.
    assert len(results) == 1
    assert results[0].home_team == "C"


def test_result_enum():
    results = parse_results(_load())
    for r in results:
        if r.home_score is not None and r.away_score is not None:
            assert r.result in ("H", "D", "A")
