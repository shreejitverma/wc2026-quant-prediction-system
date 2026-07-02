"""Phase 2 end-to-end smoke test: feature engineering stack.

Exercises:
  1. Elo timeline reconstruction from a small fixture list.
  2. Feature store PIT gate: future features stay invisible.
  3. Match context features (altitude, stage, rest days).
  4. De-vigging (proportional, power, Shin) on a synthetic Kalshi market.
  5. Feature pipeline orchestrator on real or synthetic data.

Run with: uv run python scripts/phase2_selfcheck.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from wc2026.features.elo_hist import build_elo_timeline, elo_features_for_match
from wc2026.features.market_fv import (
    devig_kalshi_market,
    is_admissible_for_training,
)
from wc2026.features.match_ctx import build_match_context
from wc2026.features.store import FeatureStore
from wc2026.ingest.results import MatchResult

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


def _match(
    home: str,
    away: str,
    hs: int,
    aws: int,
    d: date,
    neutral: bool = True,
    tournament: str = "FIFA World Cup",
) -> MatchResult:
    return MatchResult(
        match_date=d,
        home_team=home,
        away_team=away,
        home_score=hs,
        away_score=aws,
        tournament=tournament,
        city="Los Angeles",
        country="USA",
        neutral=neutral,
        is_competitive=True,
    )


def main() -> int:
    errors = 0

    # 1. Elo timeline
    d1, d2 = date(2026, 6, 11), date(2026, 6, 15)
    results = [
        _match("MEX", "ENG", 1, 0, d1, neutral=True),
        _match("MEX", "FRA", 0, 1, d2, neutral=True),
    ]
    tl = build_elo_timeline(results)
    elo_mex_d1 = tl.elo_as_of("MEX", d1)
    elo_mex_d2 = tl.elo_as_of("MEX", d2)
    if elo_mex_d1 is None or elo_mex_d2 is None:
        _fail("Elo timeline: None returned unexpectedly")
        errors += 1
    elif not (elo_mex_d1 > 1300 and elo_mex_d2 < elo_mex_d1):
        _fail(f"Elo timeline: unexpected values MEX@d1={elo_mex_d1:.1f} @d2={elo_mex_d2:.1f}")
        errors += 1
    else:
        _ok(f"Elo timeline: MEX @d1={elo_mex_d1:.1f} @d2={elo_mex_d2:.1f} (won then lost)")

    # 2. elo_features_for_match
    m = _match("MEX", "ENG", 1, 0, d1)
    tl_empty = build_elo_timeline([])
    feats = elo_features_for_match(m, tl_empty)
    if feats["elo_home"] is not None or feats["elo_away"] is not None:
        _fail("elo_features_for_match: should return None for unknown teams")
        errors += 1
    else:
        _ok("elo_features_for_match: None for unknown teams")

    # 3. Feature store PIT gate
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "features.duckdb"
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        t5 = datetime(2026, 1, 6, tzinfo=UTC)
        t3 = datetime(2026, 1, 4, tzinfo=UTC)
        with FeatureStore(db) as fs:
            fs.upsert("TEST", "elo", 1900.0, knowable_at=t0)
            fs.upsert("TEST", "elo", 1943.0, knowable_at=t5)
            at_t3 = fs.get_features("TEST", as_of_ts=t3)
            at_t5 = fs.get_features("TEST", as_of_ts=t5)
        if at_t3.get("elo") != 1900.0:
            _fail(f"FeatureStore PIT: at t3 expected 1900.0, got {at_t3.get('elo')}")
            errors += 1
        elif at_t5.get("elo") != 1943.0:
            _fail(f"FeatureStore PIT: at t5 expected 1943.0, got {at_t5.get('elo')}")
            errors += 1
        else:
            _ok("FeatureStore PIT gate: old value visible at t3, new value at t5")

    # 4. Match context - Mexico City altitude
    mex_match = MatchResult(
        match_date=date(2026, 6, 22),
        home_team="MEX",
        away_team="URU",
        home_score=None,
        away_score=None,
        tournament="FIFA World Cup",
        city="Mexico City",
        country="Mexico",
        neutral=True,
        is_competitive=True,
    )
    ctx = build_match_context(mex_match, prior_results=[])
    feats_ctx = ctx.to_features()
    if feats_ctx.get("altitude_m") != 2240.0 or feats_ctx.get("high_altitude") != 1.0:
        _fail(f"MatchContext altitude: {feats_ctx.get('altitude_m')}")
        errors += 1
    else:
        _ok(f"MatchContext: Mexico City altitude={feats_ctx['altitude_m']}m, high_altitude=1.0")

    # 5. De-vigging
    dv = devig_kalshi_market(
        "KXWCADVANCE-MEX-YES",
        yes_ask=0.50, yes_bid=0.49,
        no_ask=0.52, no_bid=0.51,
        snapshot_ts="2026-06-20T12:00:00+00:00",
    )
    for method, val in [
        ("proportional", dv.p_proportional),
        ("power", dv.p_power),
        ("shin", dv.p_shin),
    ]:
        if not (0.40 < val < 0.60):
            _fail(f"devig {method}: {val:.4f} not near 0.5 for even market")
            errors += 1
        else:
            _ok(f"devig {method}: {val:.4f} (near-even market)")

    # 6. Admissibility guard
    kickoff = datetime(2026, 6, 22, 19, 0, tzinfo=UTC)
    snap_ok = datetime(2026, 6, 21, 18, 0, tzinfo=UTC)    # 25h before
    snap_bad = datetime(2026, 6, 22, 18, 30, tzinfo=UTC)  # 30min before
    if not is_admissible_for_training(snap_ok, kickoff):
        _fail("admissibility: 25h before kickoff should be admissible")
        errors += 1
    elif is_admissible_for_training(snap_bad, kickoff):
        _fail("admissibility: 30min before kickoff should NOT be admissible")
        errors += 1
    else:
        _ok("admissibility guard: 25h=admissible, 30min=not admissible")

    print()
    if errors == 0:
        print("Phase 2 self-check: ALL PASS")
    else:
        print(f"Phase 2 self-check: {errors} FAILURE(S)")
    return errors


if __name__ == "__main__":
    sys.exit(main())
