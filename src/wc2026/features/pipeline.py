"""Feature pipeline: results → Elo timeline → features → DuckDB store.

Orchestrates Phase 2 feature computation for a batch of matches.
Designed to be called by `make daily` or a backtest runner.

Usage:
    from wc2026.features.pipeline import run_feature_pipeline
    run_feature_pipeline(
        results_csv_path="data/raw/results_international/2026-07-01/results.csv",
        db_path="data/processed/features.duckdb",
        cutoff_date=date.today(),   # only compute features for matches up to here
    )

Point-in-time safety: every feature is written with the appropriate `knowable_at`
timestamp. The Elo features for match on date D are written with
`knowable_at = D - 1 day` (the Elo was knowable before the match). The match
context features are written with `knowable_at = D - 7 days` (fixtures are
published well in advance).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from ..ingest.results import parse_results
from .elo_hist import build_elo_timeline, elo_features_for_match
from .match_ctx import _match_id, build_match_context
from .store import FeatureStore

log = logging.getLogger(__name__)


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=UTC)


def run_feature_pipeline(
    *,
    results_csv_path: str | Path,
    db_path: str | Path,
    cutoff_date: date | None = None,
    overwrite: bool = False,
) -> dict[str, int]:
    """Compute and store all Phase 2 features for all matches up to cutoff_date.

    Returns a summary dict: {"matches_processed": N, "features_written": M}.
    """
    cutoff = cutoff_date or date.today()

    # --- Parse results ---
    text = Path(results_csv_path).read_text(encoding="utf-8")
    all_results = parse_results(text)
    log.info("Loaded %d match results", len(all_results))

    # Filter to matches on or before cutoff
    results_in_window = [r for r in all_results if r.match_date <= cutoff]

    # --- Build Elo timeline ---
    timeline = build_elo_timeline(results_in_window)
    log.info("Elo timeline built for %d teams", len(timeline.all_teams()))

    # --- Write features ---
    n_matches = 0
    n_features = 0

    with FeatureStore(db_path) as fs:
        for match in results_in_window:
            mid = _match_id(match)

            # Skip if already in store and not overwriting
            if not overwrite and mid in fs.match_ids():
                continue

            # 1) Elo features (knowable_at = day before the match)
            elo_feats = elo_features_for_match(match, timeline)
            ka_elo = _date_to_utc(match.match_date - timedelta(days=1))
            fs.upsert_many(mid, elo_feats, knowable_at=ka_elo, source="elo_hist")

            # 2) Match context features (knowable_at = 7 days before kickoff; fixtures published)
            ctx = build_match_context(match, prior_results=results_in_window)
            ka_ctx = _date_to_utc(match.match_date - timedelta(days=7))
            fs.upsert_many(mid, ctx.to_features(), knowable_at=ka_ctx, source="match_ctx")

            n_matches += 1
            n_features += len(elo_feats) + len(ctx.to_features())

    log.info("Pipeline complete: %d matches, %d feature rows", n_matches, n_features)
    return {"matches_processed": n_matches, "features_written": n_features}
