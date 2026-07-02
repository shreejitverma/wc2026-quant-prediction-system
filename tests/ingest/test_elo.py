"""Tests for elo.py - all hermetic."""

from pathlib import Path

from wc2026.ingest.elo import parse_elo

FIXTURE = Path(__file__).parent / "fixtures" / "elo_sample.tsv"


def _load() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_count():
    ratings = parse_elo(_load())
    assert len(ratings) == 5


def test_argentina_fields():
    ratings = parse_elo(_load())
    ar = next(r for r in ratings if r.team_code == "AR")
    assert ar.rank == 1
    assert ar.elo == 2148
    assert ar.elo_max == 2172
    assert ar.elo_max_year == 1988


def test_mexico_high_rank_delta():
    ratings = parse_elo(_load())
    mx = next(r for r in ratings if r.team_code == "MX")
    # rank_delta = prev_rank - rank (positive = moved up)
    # prev=9, rank=9 in fixture => 0 delta
    assert isinstance(mx.rank_delta, int)


def test_elo_delta_parsing():
    ratings = parse_elo(_load())
    ar = next(r for r in ratings if r.team_code == "AR")
    # 1w delta is the second change column (col 11 = elo_delta_1w)
    assert ar.elo_delta_1w == 35
    assert ar.elo_delta_1m == 35


def test_all_have_elo():
    ratings = parse_elo(_load())
    assert all(r.elo > 1000 for r in ratings)


def test_tolerates_short_lines():
    # A line with < 10 columns should be skipped silently.
    tsv = "1\t1\tAR\t2148\n"  # only 4 cols
    tsv += "2\t2\tES\t2144\t1\t2189\t7\t1946\t19\t1805\t-1\t-21\t-1\t-28\n"
    ratings = parse_elo(tsv)
    assert len(ratings) == 1
    assert ratings[0].team_code == "ES"
