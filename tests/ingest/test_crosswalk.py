"""Tests for crosswalk.py - all hermetic."""

from pathlib import Path

import pytest

from wc2026.ingest.crosswalk import TeamCrosswalk

CROSSWALK_YAML = Path(__file__).parents[2] / "configs" / "crosswalk_teams.yaml"


def test_load_from_yaml():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert len(cw) > 40  # at least the 48 WC2026 teams


def test_resolve_canonical_name():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert cw.resolve("England") == "England"


def test_resolve_elo_code():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert cw.resolve("EN") == "England"
    assert cw.resolve("AR") == "Argentina"


def test_resolve_common_alias():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert cw.resolve("United States") == "USA"
    assert cw.resolve("Holland") == "Netherlands"


def test_resolve_none_for_unknown():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert cw.resolve("Nonexistent Nation FC") is None


def test_resolve_strict_raises():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    with pytest.raises(KeyError):
        cw.resolve_strict("Nonexistent FC")


def test_fuzzy_top_result():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    candidates = cw.fuzzy("Englond")  # deliberate typo
    assert len(candidates) > 0
    names = [c[0] for c in candidates]
    assert "England" in names


def test_fuzzy_returns_scores():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    candidates = cw.fuzzy("Brazil")
    for _name, score in candidates:
        assert 0.0 <= score <= 1.0
    # exact match should be top
    assert candidates[0][0] == "Brazil"
    assert candidates[0][1] > 0.9


def test_empty_crosswalk():
    cw = TeamCrosswalk.empty()
    assert cw.resolve("England") is None
    assert len(cw) == 0


def test_normalize_case_insensitive():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    assert cw.resolve("england") == cw.resolve("England")
    assert cw.resolve("ARGENTINA") == cw.resolve("Argentina")


def test_no_duplicate_canonicals():
    cw = TeamCrosswalk.from_yaml(CROSSWALK_YAML)
    canonicals = cw.all_canonicals()
    assert len(canonicals) == len(set(canonicals))
