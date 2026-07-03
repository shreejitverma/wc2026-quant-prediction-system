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
    killed: bool = Field(
        default=False,
        description="True when a kill command is in the ledger; re-arming is a CLI act.",
    )
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
    contract_label: str
    fair_value: float
    fair: ProbWithBand
    best_bid: float
    best_ask: float
    depth_bid: int = Field(description="Size available at best bid (contracts).")
    depth_ask: int
    edge_after_fees: float
    edge_risk_adjusted: float = Field(
        description="After-fee edge scaled by (1 - uncertainty); the board's ranking key."
    )
    uncertainty_score: float
    classification: Literal["my-info", "their-info", "settlement-trap", "incoherence"]
    actionability: Literal["Tradeable", "Watch", "No Edge", "Unsafe", "Stale"]
    decomposition: list[FairValueStep] = Field(
        description="Fair-value waterfall; the last step's value_after equals fair.p."
    )
    settlement: SettlementMapping


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


# --- Opportunity Board + coherence (Phase 3). Additive extension of
# MarketOpportunity (non-breaking); shapes mirror pricing/{fair_value,
# coherence,mapper}. Served source="mock" until pricing persists artifacts. ---


class FairValueStep(BaseModel):
    """One step of the fair-value waterfall. Steps are ordered; value_after of
    the last step IS the fair value - the decomposition must account for the
    whole number or it is not a decomposition."""

    label: Literal["model_probability", "fees", "timing_lockup", "resolution_risk"]
    delta: float = Field(description="Signed contribution; the first step's delta is the model prob itself.")
    value_after: float


class SettlementMapping(BaseModel):
    """The market's settlement text mapped to the model event it prices.
    `confirmed=False` quarantines the contract: settlement-definition traps are
    an edge CLASS, and an unreviewed mapping must be unactionable."""

    market_text: str
    model_event: str
    confirmed: bool
    confirmed_at: str | None = None
    note: str | None = None


class CrossVenueRow(BaseModel):
    event: str
    kalshi: float | None
    polymarket: float | None
    devig_ref: float | None = Field(description="De-vigged sharp-book reference, if available.")
    max_spread_pp: float


class InternalViolation(BaseModel):
    """Bracket-path product vs direct price, from the persisted joint draws."""

    description: str
    product_price: float
    direct_price: float
    gap_pp: float
    safest_class: Literal["my-info", "their-info", "settlement-trap", "incoherence"]


class CoherenceReport(BaseModel):
    cross_venue: list[CrossVenueRow]
    internal: list[InternalViolation]


# --- Tournament + joint-query (Phase 2/3). Every probability is COUNTED from
# the draw table (mock_tournament.py now; the simulator's persisted draws
# later), so n and Wilson CIs are real arithmetic. ---


class TeamGroupProbs(BaseModel):
    team: str
    p_first: float
    p_second: float
    p_third: float
    p_best_third_qualify: float = Field(
        description="P(finishes 3rd AND advances among the 8 best thirds)."
    )
    p_advance: float = Field(description="P(reaches the round of 32 by any path).")


class GroupTable(BaseModel):
    group: str
    teams: list[TeamGroupProbs]


class ThirdPlaceCandidate(BaseModel):
    team: str
    group: str
    p_third: float
    p_qualify_given_third: float
    p_best_third_qualify: float


class AdvancementRow(BaseModel):
    team: str
    p_r32: float
    p_r16: float
    p_qf: float
    p_sf: float
    p_final: float
    p_champion: float


class WinnerProb(BaseModel):
    team: str
    p: ProbWithBand = Field(description="Wilson 95% interval from draw counts.")


class TournamentState(BaseModel):
    n_draws: int
    groups: list[GroupTable]
    third_place_race: list[ThirdPlaceCandidate]
    advancement: list[AdvancementRow] = Field(description="Sorted by p_champion desc.")
    winner: list[WinnerProb] = Field(description="Top teams by championship probability.")


class SimQueryEvent(BaseModel):
    team: str
    outcome: Literal[
        "wins_group",
        "qualifies",
        "reaches_r16",
        "reaches_qf",
        "reaches_sf",
        "reaches_final",
        "champion",
    ]


class SimQueryRequest(BaseModel):
    events: list[SimQueryEvent] = Field(min_length=1, max_length=4)


class SimQueryResult(BaseModel):
    events: list[SimQueryEvent]
    p: ProbWithBand = Field(description="Joint probability, Wilson 95% from counts.")
    n_draws: int
    n_hits: int
    independent_product: float = Field(
        description="Product of the marginal probabilities - what naive multiplication says."
    )
    dependence_ratio: float | None = Field(
        description="p / independent_product; the coherence edge lives in this ratio. Null if product is 0."
    )


# --- MM Console + fenced commands (Phase 4). Command state is REAL (derived
# from ledger command entries); book/fills/portfolio are mock until execution
# runs. Quote math routes through the real execution.quoting engine. ---


class BookLevel(BaseModel):
    price: float
    size: int


class MyQuotes(BaseModel):
    bid: float
    ask: float
    size: int
    active: bool = Field(description="False when paused or killed - quotes pulled.")


class QuoteInputs(BaseModel):
    """The quote formula's INPUTS, not just its output (Avellaneda-Stoikov via
    execution.quoting). The operator must see why the spread/skew is what it is."""

    fair_value: float
    variance: float
    inventory: float
    time_to_settlement_days: float
    gamma: float
    fee_floor: float
    widen_factor: float
    news_state: Literal["normal", "lineup-window", "post-goal", "quarantined"]
    bid: float
    ask: float
    spread: float
    skew: float = Field(description="Reservation-price shift vs fair value (inventory shade).")


class Fill(BaseModel):
    ts_utc: str
    ticker: str
    side: Literal["buy", "sell"]
    price: float
    size: int
    context: str = Field(description="What was happening when this fill occurred.")


class ConsoleState(BaseModel):
    ticker: str
    book_bids: list[BookLevel]
    book_asks: list[BookLevel]
    book_as_of: str
    my_quotes: MyQuotes
    quote_inputs: QuoteInputs
    quoting_status: Literal["active", "paused", "killed"]
    fills: list[Fill]


class ClusterPosition(BaseModel):
    ticker: str
    qty: int
    avg_price: float
    mark: float


class PositionCluster(BaseModel):
    cluster_id: str
    label: str
    net_exposure_usd: float
    limit_usd: float
    utilization: float = Field(description="abs(exposure)/limit; >=1.0 means at/over limit.")
    optimizer_target_usd: float = Field(description="Convex-optimizer target for this cluster.")
    positions: list[ClusterPosition]


class PortfolioState(BaseModel):
    clusters: list[PositionCluster]
    total_exposure_usd: float
    risk_budget_usd: float


class CommandStateOut(BaseModel):
    killed: bool
    killed_at: str | None
    kill_reason: str | None
    paused_tickers: dict[str, str] = Field(description="ticker -> UTC ISO time it was paused.")
    widen_factor: float


class CommandResult(BaseModel):
    accepted: bool
    already: bool = Field(description="True when idempotence made this a no-op (no new ledger entry).")
    ledger_seq: int | None = Field(description="Ledger seq of the appended command entry, if one was written.")
    state: CommandStateOut


class KillRequest(BaseModel):
    reason: str = Field(min_length=3, description="Ledgered verbatim; 'why' is part of the audit trail.")


class PauseResumeRequest(BaseModel):
    reason: str | None = None


class WidenRequest(BaseModel):
    factor: float = Field(description="Spread multiplier; clamped server-side to [1.0, 3.0].")


# --- Ops + alerts (Phase 6 core). Alerts are mock until the alert engine
# runs; ACK STATE IS REAL (ledger command fold). Freshness matrix is mock
# until ingestion persists snapshots; pipeline runs are real (runs.jsonl). ---


class Alert(BaseModel):
    alert_id: str
    ts_utc: str
    severity: Literal["info", "warn", "critical"]
    kind: Literal["calibration_drift", "divergence", "stale_source", "reconciliation"]
    message: str = Field(
        description="Carries its own diagnosis discipline (e.g. divergence copy says check freshness FIRST)."
    )
    acked: bool
    acked_at: str | None


class AlertsPage(BaseModel):
    alerts: list[Alert]
    unacked: int = Field(description="Pre-computed so the status strip never counts client-side.")


class FreshnessSource(BaseModel):
    source: str
    last_success_utc: str
    staleness_seconds: float
    max_age_seconds: int
    status: Literal["ok", "stale", "down"]


class ReconciliationRow(BaseModel):
    venue: str
    status: Literal["match", "mismatch", "unknown"]
    detail: str


class OpsFreshness(BaseModel):
    sources: list[FreshnessSource]
    reconciliation: list[ReconciliationRow]
