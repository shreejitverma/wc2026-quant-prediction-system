"""Versioned API response schemas (ADR-0012).

Every response body is `Envelope[T] = {data, provenance}`.
Provenance is not optional metadata: it is how the UI refuses to display a number
without knowing how fresh it is and which run/config produced it.
`source="mock"` is load-bearing - endpoints not yet wired to real pipeline
artifacts must say so, and the UI renders them visibly quarantined.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: Literal["real", "mock"] = Field(
        description="'real' = read from pipeline artifacts; 'mock' = generated placeholder."
    )
    generated_at: str = Field(description="UTC ISO-8601 time this response was assembled.")
    data_as_of: str | None = Field(
        default=None,
        description="UTC ISO-8601 timestamp of the newest underlying datum; null = no data yet.",
    )
    run_id: str | None = Field(default=None, description="Run that produced the data, if any.")
    git_commit: str | None = Field(default=None, description="Serving code's git commit.")
    config_hash: str = Field(description="Content hash of the active AppConfig.")


class Envelope[T](BaseModel):
    data: T
    provenance: Provenance


# --- Health -------------------------------------------------------------


class VenueStatus(BaseModel):
    kalshi_enabled: bool
    polymarket_enabled: bool


class HealthData(BaseModel):
    mode: Literal["paper", "live"]
    data_status: Literal["ok", "stale", "empty"] = Field(
        description="'empty' = no ledger entries exist yet (definitive, not an error)."
    )
    ledger_entries: int
    last_ledger_ts_utc: str | None
    ledger_staleness_seconds: float | None
    max_data_staleness_seconds: int
    min_edge: float
    kill_switch_enabled: bool
    venues: VenueStatus


# --- Ledger -------------------------------------------------------------


class LedgerEntry(BaseModel):
    seq: int
    ts_utc: str
    kind: str
    prev_hash: str
    row_hash: str
    payload: Any


class LedgerPage(BaseModel):
    entries: list[LedgerEntry]
    total_entries: int = Field(description="Entries in the whole ledger, pre-filter.")
    returned: int
    has_more: bool = Field(description="True if the filter matched more rows than `limit`.")


class LedgerVerification(BaseModel):
    valid: bool
    entries: int
    path: str


# --- Runs ---------------------------------------------------------------


class RunOut(BaseModel):
    """A wc2026.runs.RunRecord as stored in the runs ledger, plus its chain position."""

    run_id: str
    created_at: str
    git_commit: str | None
    git_dirty: bool | None
    config_hash: str
    data_snapshot_hash: str | None
    features_hash: str | None
    model_name: str
    model_version: str
    metrics: dict[str, Any]
    notes: str
    ledger_seq: int
    row_hash: str


class RunsPage(BaseModel):
    runs: list[RunOut]
    total_runs: int


# --- Mock-only shapes (scaffold-compatible; always served with source="mock") ---


class MatchPrediction(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    expected_goals_home: float
    expected_goals_away: float
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    scoreline_matrix: list[list[float]]
    uncertainty_score: float
    freshness_utc: str


class MarketOpportunity(BaseModel):
    venue: Literal["kalshi", "polymarket"]
    ticker: str
    fair_value: float
    best_bid: float
    best_ask: float
    edge_after_fees: float
    actionability: Literal["Tradeable", "Watch", "No Edge", "Unsafe", "Stale"]


# --- Match Detail (Phase 2). Shapes mirror what the pipeline will persist:
# ScoreDist matrices per model (models/base.py), meta-ensemble weights
# (models/meta_ensemble.py), and a de-vigged market baseline (features/market_fv).
# Served source="mock" until those artifacts exist on disk. ---


class VenueInfo(BaseModel):
    name: str
    city: str
    tz: str = Field(description="IANA zone of the venue, e.g. America/Mexico_City.")
    altitude_m: int
    heat_risk: Literal["low", "moderate", "high"]


class LineupStatus(BaseModel):
    """Lineup confirmation is the biggest single information event before
    kickoff; the UI renders its arrival unmissably."""

    state: Literal["expected", "confirmed"]
    as_of: str = Field(description="UTC ISO time this status was last checked.")
    confirmed_at: str | None = Field(
        default=None, description="UTC ISO time official lineups were published, if they were."
    )


class ProbWithBand(BaseModel):
    """A probability may not travel without its uncertainty (ADR-0013)."""

    p: float
    lo: float
    hi: float


class ModelProbs(BaseModel):
    model: str
    version: str
    weight: float | None = Field(
        description="Ensemble weight in force for this market type; null for the market baseline row."
    )
    p_home: float
    p_draw: float
    p_away: float
    p_over_2_5: float
    p_btts: float


class MarketBaseline(BaseModel):
    """De-vigged 1X2 from the sharpest available book: the comparison line the
    model board is judged against."""

    venue: str
    as_of: str
    overround: float = Field(description="Total implied prob before de-vig, e.g. 1.045.")
    p_home: float
    p_draw: float
    p_away: float


class Attribution(BaseModel):
    """Why the ensemble disagrees with the market, one feature at a time, in
    football language. delta_pp is signed percentage points toward `direction`."""

    feature: str
    direction: Literal["home", "draw", "away", "over", "under"]
    delta_pp: float
    note: str


class MatchDetail(BaseModel):
    match_id: str
    group: str | None
    home_team: str
    away_team: str
    kickoff_utc: str
    venue: VenueInfo
    rest_days_home: int
    rest_days_away: int
    lineup: LineupStatus
    expected_goals_home: float
    expected_goals_away: float
    scoreline_matrix: list[list[float]] = Field(
        description="Ensemble goals matrix [home][away]; sums to ~1 including the tail."
    )
    prob_home_win: ProbWithBand
    prob_draw: ProbWithBand
    prob_away_win: ProbWithBand
    prob_over_2_5: ProbWithBand
    prob_btts: ProbWithBand
    models: list[ModelProbs] = Field(description="Per-model outputs; ensemble is NOT in this list.")
    ensemble: ModelProbs
    market: MarketBaseline
    why: list[Attribution]
    freshness_utc: str


class TimelinePoint(BaseModel):
    ts_utc: str
    market: float | None = Field(description="Market mid for the contract; null if no quote.")
    fair: float
    lo: float
    hi: float


class TimelineEvent(BaseModel):
    ts_utc: str
    kind: Literal["lineup", "goal_elsewhere", "news"]
    label: str


class MatchTimeline(BaseModel):
    match_id: str
    contract: str = Field(description="Which contract the series prices, e.g. 'home win'.")
    points: list[TimelinePoint]
    events: list[TimelineEvent]
