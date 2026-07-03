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
