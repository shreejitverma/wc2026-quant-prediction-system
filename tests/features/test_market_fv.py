"""Tests for de-vigging methods and market feature admissibility."""

from datetime import UTC, datetime, timedelta

from wc2026.features.market_fv import (
    _power_devig,
    _proportional_devig,
    _shin_devig,
    devig_kalshi_market,
    is_admissible_for_training,
    market_features_for_match,
)

# Near-even market (roughly 50/50)
_YES_ASK, _YES_BID = 0.50, 0.49
_NO_ASK, _NO_BID = 0.52, 0.51


def test_proportional_sums_to_one():
    """De-vigged probabilities for a binary market must sum to 1.0."""
    p = _proportional_devig(0.52, 0.52)
    assert abs(p - 0.5) < 0.01  # symmetric overround -> exactly 0.5


def test_proportional_favorite():
    p = _proportional_devig(0.70, 0.34)  # favorite at 70¢ raw
    q = _proportional_devig(0.34, 0.70)
    assert abs(p + q - 1.0) < 0.001
    assert p > 0.5


def test_power_near_even():
    p = _power_devig(0.52, 0.52)
    assert abs(p - 0.5) < 0.02


def test_power_favorite():
    p = _power_devig(0.70, 0.34)
    q = _power_devig(0.34, 0.70)
    assert abs(p + q - 1.0) < 0.01


def test_shin_near_even():
    p = _shin_devig(0.52, 0.52)
    assert abs(p - 0.5) < 0.05


def test_shin_favorite():
    p = _shin_devig(0.70, 0.34)
    q = _shin_devig(0.34, 0.70)
    # Shin should preserve rough symmetry
    assert p > 0.5
    assert abs(p + q - 1.0) < 0.05


def test_all_three_methods_consistent_near_even():
    """Near-even market: all three should be close to 0.5."""
    dv = devig_kalshi_market(
        "KXWCADVANCE-TEST",
        _YES_ASK, _YES_BID, _NO_ASK, _NO_BID,
        snapshot_ts="2026-07-05T17:00:00+00:00",
    )
    for p in (dv.p_proportional, dv.p_power, dv.p_shin):
        assert 0.40 < p < 0.60, f"Expected near 0.5, got {p}"


def test_admissibility_24h_before():
    kickoff = datetime(2026, 7, 5, 19, 0, tzinfo=UTC)
    snap = kickoff - timedelta(hours=25)
    assert is_admissible_for_training(snap, kickoff) is True


def test_not_admissible_30min_before():
    kickoff = datetime(2026, 7, 5, 19, 0, tzinfo=UTC)
    snap = kickoff - timedelta(minutes=30)
    assert is_admissible_for_training(snap, kickoff) is False


def test_market_features_dict_keys():
    dv = devig_kalshi_market(
        "TEST", _YES_ASK, _YES_BID, _NO_ASK, _NO_BID,
        snapshot_ts="2026-07-05T17:00:00+00:00",
    )
    snap_ts = datetime(2026, 7, 5, 17, 0, tzinfo=UTC)
    kickoff = datetime(2026, 7, 5, 19, 0, tzinfo=UTC)
    feats = market_features_for_match(dv, snapshot_ts=snap_ts, kickoff_ts=kickoff)
    # Not admissible (only 2h before kickoff) -> all prices None
    assert feats["kalshi_admissible"] == 0.0
    assert feats["kalshi_p_proportional"] is None


def test_market_features_admissible():
    dv = devig_kalshi_market(
        "TEST", _YES_ASK, _YES_BID, _NO_ASK, _NO_BID,
        snapshot_ts="2026-07-05T17:00:00+00:00",
    )
    snap_ts = datetime(2026, 7, 4, 10, 0, tzinfo=UTC)  # 33h before
    kickoff = datetime(2026, 7, 5, 19, 0, tzinfo=UTC)
    feats = market_features_for_match(dv, snapshot_ts=snap_ts, kickoff_ts=kickoff)
    assert feats["kalshi_admissible"] == 1.0
    assert feats["kalshi_p_proportional"] is not None
    assert 0.3 < feats["kalshi_p_proportional"] < 0.7


def test_live_prediction_no_kickoff_ts():
    """Without kickoff_ts (live mode), all features returned unconditionally."""
    dv = devig_kalshi_market(
        "TEST", _YES_ASK, _YES_BID, _NO_ASK, _NO_BID,
        snapshot_ts="2026-07-05T17:00:00+00:00",
    )
    snap_ts = datetime(2026, 7, 5, 18, 55, tzinfo=UTC)  # 5min before kickoff
    feats = market_features_for_match(dv, snapshot_ts=snap_ts, kickoff_ts=None)
    assert feats["kalshi_admissible"] == 1.0
    assert feats["kalshi_p_proportional"] is not None
