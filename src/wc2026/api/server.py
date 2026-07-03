"""WC2026 terminal API (ADR-0011, ADR-0012).

Read paths are generous; write paths do not exist yet (Phase 4 adds the fenced
command endpoints, each of which becomes a ledger entry via the backend).

Three endpoint groups are REAL and read the same JSONL artifacts the CLI writes:
  - /api/v1/health         config fences + ledger freshness
  - /api/v1/ledger[...]    hash-chained audit log, paginated, verifiable
  - /api/v1/runs[...]      reproducible run records

Matches/opportunities remain MOCK until the model -> simulator -> pricing path
persists real artifacts. They are deterministic (seeded from config), labeled
provenance.source="mock", and the UI quarantines them behind a banner. Serving
unlabeled mock data is the failure mode this file exists to prevent.

Run: make api   (uvicorn on 127.0.0.1:8000; localhost-only by design - the
frontend is the only client, and exchange credentials never enter this process
until the execution phase, where they stay server-side).
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from ..eval.metrics import bootstrap_ci, diebold_mariano, pointwise_brier, pointwise_log_loss
from ..execution.portfolio import PortfolioOptimizer
from ..execution.quoting import QuotingEngine
from ..ledger import AppendOnlyLedger
from ..time_utils import from_iso, to_iso, utc_now
from .commands import (
    CommandRejected,
    CommandState,
    command_ack_alert,
    command_kill,
    command_pause,
    command_resume,
    command_widen,
    read_command_state,
)
from .deps import ApiState, get_state
from .mock_eval import MARKET_CLASSES, eval_table
from .mock_tournament import (
    GROUPS,
    STAGE_CHAMPION,
    STAGE_FINAL,
    STAGE_QF,
    STAGE_R16,
    STAGE_R32,
    STAGE_SF,
    draw_table,
    wilson_ci,
)
from .provenance import make_provenance
from .schemas import (
    AdvancementRow,
    Alert,
    AlertsPage,
    Attribution,
    BookLevel,
    CalibrationBin,
    CalibrationReport,
    CIValue,
    ClusterPosition,
    ClvByClass,
    ClvHistBin,
    ClvPoint,
    ClvReport,
    CoherenceReport,
    CommandResult,
    CommandStateOut,
    ConsoleState,
    CrossVenueRow,
    Envelope,
    FairValueStep,
    Fill,
    FreshnessSource,
    GroupTable,
    HealthData,
    InternalViolation,
    KillRequest,
    LedgerEntry,
    LedgerPage,
    LedgerVerification,
    LineupStatus,
    MarketBaseline,
    MarketOpportunity,
    MatchDetail,
    MatchPrediction,
    MatchTimeline,
    ModelProbs,
    ModelRaceReport,
    MyQuotes,
    OpsFreshness,
    PauseResumeRequest,
    PnlPoint,
    PnlReport,
    PortfolioState,
    PositionCluster,
    PreregGate,
    PreregPage,
    ProbWithBand,
    QuoteInputs,
    RaceRow,
    ReconciliationRow,
    RunOut,
    RunsPage,
    SettlementMapping,
    SimQueryRequest,
    SimQueryResult,
    TeamGroupProbs,
    ThirdPlaceCandidate,
    TimelineEvent,
    TimelinePoint,
    TournamentState,
    VenueInfo,
    VenueStatus,
    WeightsPoint,
    WidenRequest,
    WinnerProb,
)
from .ws import serve_ws

StateDep = Annotated[ApiState, Depends(get_state)]

app = FastAPI(title="WC2026 Terminal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Localhost-only, explicit origins: this is a single-operator terminal,
    # not a public API. Wildcard CORS on a process that will later hold
    # positions is how a random browser tab gets to call your kill switch.
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health (REAL) --------------------------------------------------------


def build_health_envelope(state: ApiState) -> Envelope[HealthData]:
    """Config fences + ledger freshness. Shared by the REST route and the WS
    `health` topic so both channels serve byte-identical envelopes.

    Ledger recency is the best available "is anything happening" signal today;
    the per-source freshness matrix arrives in Phase 6 once ingestion actually
    writes snapshots.
    """
    entries = AppendOnlyLedger(state.ledger_path).read_all()
    last_ts = str(entries[-1]["ts_utc"]) if entries else None
    staleness = (utc_now() - from_iso(last_ts)).total_seconds() if last_ts else None
    max_stale = state.cfg.kill_switch.max_data_staleness_seconds

    if not entries:
        data_status = "empty"
    elif staleness is not None and staleness > max_stale:
        data_status = "stale"
    else:
        data_status = "ok"

    data = HealthData(
        mode=state.cfg.mode,
        data_status=data_status,
        ledger_entries=len(entries),
        last_ledger_ts_utc=last_ts,
        ledger_staleness_seconds=staleness,
        max_data_staleness_seconds=max_stale,
        min_edge=state.cfg.risk.min_edge,
        kill_switch_enabled=state.cfg.kill_switch.enabled,
        killed=read_command_state(state).killed,
        venues=VenueStatus(
            kalshi_enabled=state.cfg.venues.kalshi_enabled,
            polymarket_enabled=state.cfg.venues.polymarket_enabled,
        ),
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="real", data_as_of=last_ts))


@app.get("/api/v1/health", response_model=Envelope[HealthData])
def get_health(state: StateDep) -> Envelope[HealthData]:
    return build_health_envelope(state)


# --- Ledger (REAL) --------------------------------------------------------


@app.get("/api/v1/ledger", response_model=Envelope[LedgerPage])
def read_ledger(
    state: StateDep,
    after_seq: int = Query(default=-1, description="Return entries with seq > after_seq."),
    kind: str | None = Query(default=None, description="Filter by entry kind."),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Envelope[LedgerPage]:
    all_entries = AppendOnlyLedger(state.ledger_path).read_all()
    matched = [
        e for e in all_entries if int(e["seq"]) > after_seq and (kind is None or e["kind"] == kind)
    ]
    page = matched[:limit]
    data = LedgerPage(
        entries=[LedgerEntry(**e) for e in page],
        total_entries=len(all_entries),
        returned=len(page),
        has_more=len(matched) > limit,
    )
    data_as_of = str(all_entries[-1]["ts_utc"]) if all_entries else None
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="real", data_as_of=data_as_of))


@app.get("/api/v1/ledger/verify", response_model=Envelope[LedgerVerification])
def verify_ledger(state: StateDep) -> Envelope[LedgerVerification]:
    led = AppendOnlyLedger(state.ledger_path)
    data = LedgerVerification(
        valid=led.verify_chain(),
        entries=len(led),
        path=str(state.ledger_path.relative_to(state.root)),
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="real"))


# --- Runs (REAL) ----------------------------------------------------------


def _read_runs(state: ApiState) -> tuple[list[RunOut], str | None]:
    entries = AppendOnlyLedger(state.runs_path).read_all()
    runs = [
        RunOut(**e["payload"], ledger_seq=int(e["seq"]), row_hash=str(e["row_hash"]))
        for e in entries
        if e["kind"] == "run"
    ]
    data_as_of = str(entries[-1]["ts_utc"]) if entries else None
    return runs, data_as_of


@app.get("/api/v1/runs", response_model=Envelope[RunsPage])
def list_runs(
    state: StateDep,
    limit: int = Query(default=50, ge=1, le=500),
) -> Envelope[RunsPage]:
    runs, data_as_of = _read_runs(state)
    newest_first = sorted(runs, key=lambda r: r.ledger_seq, reverse=True)
    data = RunsPage(runs=newest_first[:limit], total_runs=len(runs))
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="real", data_as_of=data_as_of))


@app.get("/api/v1/runs/{run_id}", response_model=Envelope[RunOut])
def get_run(run_id: str, state: StateDep) -> Envelope[RunOut]:
    runs, data_as_of = _read_runs(state)
    for r in runs:
        if r.run_id == run_id:
            return Envelope(
                data=r,
                provenance=make_provenance(
                    state.cfg, source="real", data_as_of=data_as_of, run_id=run_id
                ),
            )
    raise HTTPException(status_code=404, detail={"code": "run_not_found", "run_id": run_id})


# --- Matches / Opportunities (MOCK until the pipeline persists artifacts) ---


def _poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _mock_scorelines(lam_home: float, lam_away: float, max_goals: int = 8) -> list[list[float]]:
    """Independent-Poisson goals matrix, renormalized. Internally coherent mock:
    the 1X2 probabilities served alongside are derived from this same matrix."""
    m = [
        [_poisson_pmf(lam_home, h) * _poisson_pmf(lam_away, a) for a in range(max_goals + 1)]
        for h in range(max_goals + 1)
    ]
    total = sum(sum(row) for row in m)
    return [[p / total for p in row] for row in m]


def _derive_probs(m: list[list[float]]) -> dict[str, float]:
    """All headline probabilities from ONE matrix, so nothing served alongside
    the matrix can contradict it."""
    n = len(m)
    return {
        "home": sum(m[h][a] for h in range(n) for a in range(n) if h > a),
        "draw": sum(m[k][k] for k in range(n)),
        "away": sum(m[h][a] for h in range(n) for a in range(n) if h < a),
        "over_2_5": sum(m[h][a] for h in range(n) for a in range(n) if h + a > 2.5),
        "btts": sum(m[h][a] for h in range(1, n) for a in range(1, n)),
    }


# Static fixture facts (venues are real 2026 hosts; matchups are mock).
_MOCK_FIXTURES = [
    {
        "home": "USA",
        "away": "England",
        "group": "D",
        "venue": VenueInfo(
            name="Estadio Azteca", city="Mexico City", tz="America/Mexico_City",
            altitude_m=2240, heat_risk="moderate",
        ),
        "kickoff_in_h": 6,
        "rest_home": 5,
        "rest_away": 3,
        "lineup_confirmed": True,
    },
    {
        "home": "Brazil",
        "away": "Argentina",
        "group": "A",
        "venue": VenueInfo(
            name="AT&T Stadium", city="Arlington", tz="America/Chicago",
            altitude_m=184, heat_risk="high",
        ),
        "kickoff_in_h": 30,
        "rest_home": 4,
        "rest_away": 4,
        "lineup_confirmed": False,
    },
    {
        "home": "France",
        "away": "Spain",
        "group": "C",
        "venue": VenueInfo(
            name="MetLife Stadium", city="East Rutherford", tz="America/New_York",
            altitude_m=3, heat_risk="low",
        ),
        "kickoff_in_h": 54,
        "rest_home": 6,
        "rest_away": 3,
        "lineup_confirmed": False,
    },
]

# (model, version, ensemble weight for 1X2). Names mirror wc2026.models.*.
_MODEL_SUITE = [
    ("dixon_coles", "1.2.0", 0.35),
    ("hierarchical", "0.9.1", 0.25),
    ("state_space", "0.7.0", 0.15),
    ("player_agg", "0.4.2", 0.10),
    ("gbm", "1.1.0", 0.10),
    ("market_implied", "1.0.0", 0.05),
]


def _mock_match_core(state: ApiState, idx: int) -> dict:
    """Everything both match endpoints derive from, per fixture, deterministic.

    Internally coherent by construction: each model gets its own goals matrix,
    the ensemble matrix is the weight-average of those, and every probability
    (1X2, totals, BTTS) is derived from the matrix it claims to come from.
    """
    fx = _MOCK_FIXTURES[idx]
    rng = random.Random(state.cfg.seed * 1000 + idx)
    lam_h = round(rng.uniform(0.8, 2.4), 2)
    lam_a = round(rng.uniform(0.6, 2.0), 2)

    per_model: list[tuple[str, str, float, list[list[float]]]] = []
    for name, version, weight in _MODEL_SUITE:
        jitter_h = lam_h * (1 + rng.uniform(-0.12, 0.12))
        jitter_a = lam_a * (1 + rng.uniform(-0.12, 0.12))
        per_model.append((name, version, weight, _mock_scorelines(jitter_h, jitter_a)))

    n = len(per_model[0][3])
    ensemble_matrix = [
        [sum(w * m[h][a] for _, _, w, m in per_model) for a in range(n)] for h in range(n)
    ]
    ens = _derive_probs(ensemble_matrix)

    # De-vigged market baseline: near the ensemble but not equal to it.
    raw = {k: max(0.02, ens[k] + rng.uniform(-0.035, 0.035)) for k in ("home", "draw", "away")}
    z = sum(raw.values())
    market = {k: v / z for k, v in raw.items()}

    uncertainty = rng.uniform(0.2, 0.8)
    return {
        "fixture": fx,
        "lam": (lam_h, lam_a),
        "per_model": per_model,
        "ensemble_matrix": ensemble_matrix,
        "ens": ens,
        "market": market,
        "uncertainty": uncertainty,
        "band_half": max(0.015, uncertainty * 0.05),
    }


@app.get("/api/v1/matches", response_model=Envelope[list[MatchPrediction]])
def get_matches(state: StateDep) -> Envelope[list[MatchPrediction]]:
    now_iso = to_iso(utc_now())
    matches = []
    for i in range(len(_MOCK_FIXTURES)):
        core = _mock_match_core(state, i)
        fx, (lam_h, lam_a), ens = core["fixture"], core["lam"], core["ens"]
        matches.append(
            MatchPrediction(
                match_id=f"MOCK_M{i}",
                home_team=fx["home"],
                away_team=fx["away"],
                expected_goals_home=lam_h,
                expected_goals_away=lam_a,
                prob_home_win=ens["home"],
                prob_draw=ens["draw"],
                prob_away_win=ens["away"],
                scoreline_matrix=core["ensemble_matrix"],
                uncertainty_score=core["uncertainty"],
                freshness_utc=now_iso,
            )
        )
    return Envelope(data=matches, provenance=make_provenance(state.cfg, source="mock"))


def _match_index_or_404(match_id: str) -> int:
    if match_id.startswith("MOCK_M"):
        try:
            idx = int(match_id.removeprefix("MOCK_M"))
        except ValueError:
            idx = -1
        if 0 <= idx < len(_MOCK_FIXTURES):
            return idx
    raise HTTPException(status_code=404, detail={"code": "match_not_found", "match_id": match_id})


@app.get("/api/v1/matches/{match_id}", response_model=Envelope[MatchDetail])
def get_match_detail(match_id: str, state: StateDep) -> Envelope[MatchDetail]:
    idx = _match_index_or_404(match_id)
    core = _mock_match_core(state, idx)
    fx, (lam_h, lam_a) = core["fixture"], core["lam"]
    ens, market, half = core["ens"], core["market"], core["band_half"]
    now = utc_now()
    now_iso = to_iso(now)
    kickoff = now.timestamp() + fx["kickoff_in_h"] * 3600

    def band(p: float) -> ProbWithBand:
        return ProbWithBand(p=p, lo=max(0.0, p - half), hi=min(1.0, p + half))

    def model_row(name: str, version: str, weight: float | None, m: list[list[float]]) -> ModelProbs:
        d = _derive_probs(m)
        return ModelProbs(
            model=name, version=version, weight=weight,
            p_home=d["home"], p_draw=d["draw"], p_away=d["away"],
            p_over_2_5=d["over_2_5"], p_btts=d["btts"],
        )

    # Attributions sum EXACTLY to the ensemble-market home gap: the "why" panel
    # accounts for the whole disagreement or it is not an explanation.
    gap_pp = (ens["home"] - market["home"]) * 100
    direction = "home" if gap_pp >= 0 else "away"
    parts = [round(gap_pp * s, 2) for s in (0.5, 0.3)]
    parts.append(round(gap_pp - sum(parts), 2))
    why = [
        Attribution(
            feature="rest_days_differential", direction=direction, delta_pp=abs(parts[0]),
            note=f"{fx['home']} on {fx['rest_home']}d rest vs {fx['rest_away']}d - fatigue curve favors the fresher XI.",
        ),
        Attribution(
            feature="venue_adaptation", direction=direction, delta_pp=abs(parts[1]),
            note=f"{fx['venue'].name} at {fx['venue'].altitude_m}m / heat {fx['venue'].heat_risk}: model prices acclimatization, market appears not to.",
        ),
        Attribution(
            feature="market_xg_lag", direction=direction, delta_pp=abs(parts[2]),
            note="De-vigged line still reflects pre-tournament xG; model has updated on group-stage shot quality.",
        ),
    ]

    detail = MatchDetail(
        match_id=match_id,
        group=fx["group"],
        home_team=fx["home"],
        away_team=fx["away"],
        kickoff_utc=to_iso(datetime.fromtimestamp(kickoff, tz=UTC)),
        venue=fx["venue"],
        rest_days_home=fx["rest_home"],
        rest_days_away=fx["rest_away"],
        lineup=LineupStatus(
            state="confirmed" if fx["lineup_confirmed"] else "expected",
            as_of=now_iso,
            confirmed_at=to_iso(datetime.fromtimestamp(now.timestamp() - 40 * 60, tz=UTC))
            if fx["lineup_confirmed"]
            else None,
        ),
        expected_goals_home=lam_h,
        expected_goals_away=lam_a,
        scoreline_matrix=core["ensemble_matrix"],
        prob_home_win=band(ens["home"]),
        prob_draw=band(ens["draw"]),
        prob_away_win=band(ens["away"]),
        prob_over_2_5=band(ens["over_2_5"]),
        prob_btts=band(ens["btts"]),
        models=[model_row(n, v, w, m) for n, v, w, m in core["per_model"]],
        ensemble=model_row("ensemble", "meta-1.0", None, core["ensemble_matrix"]),
        market=MarketBaseline(
            venue="kalshi",
            as_of=to_iso(datetime.fromtimestamp(now.timestamp() - 15 * 60, tz=UTC)),
            overround=1.045,
            p_home=market["home"],
            p_draw=market["draw"],
            p_away=market["away"],
        ),
        why=why,
        freshness_utc=now_iso,
    )
    return Envelope(data=detail, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/matches/{match_id}/timeline", response_model=Envelope[MatchTimeline])
def get_match_timeline(match_id: str, state: StateDep) -> Envelope[MatchTimeline]:
    idx = _match_index_or_404(match_id)
    core = _mock_match_core(state, idx)
    rng = random.Random(state.cfg.seed * 7000 + idx)
    ens_home, mkt_home, half = core["ens"]["home"], core["market"]["home"], core["band_half"]

    now_s = utc_now().timestamp()
    lineup_at = now_s - 6 * 3600  # fair value steps when the lineup news lands
    points: list[TimelinePoint] = []
    for hours_ago in range(48, -1, -1):
        t = now_s - hours_ago * 3600
        fair = ens_home - 0.02 if t < lineup_at else ens_home
        frac = 1 - hours_ago / 48
        market = mkt_home * (1 - frac) + fair * frac + rng.uniform(-0.012, 0.012)
        points.append(
            TimelinePoint(
                ts_utc=to_iso(datetime.fromtimestamp(t, tz=UTC)),
                market=round(min(0.99, max(0.01, market)), 4),
                fair=round(fair, 4),
                lo=round(max(0.0, fair - half), 4),
                hi=round(min(1.0, fair + half), 4),
            )
        )
    events = [
        TimelineEvent(
            ts_utc=to_iso(datetime.fromtimestamp(now_s - 30 * 3600, tz=UTC)),
            kind="news",
            label="Keeper fitness doubt reported",
        ),
        TimelineEvent(
            ts_utc=to_iso(datetime.fromtimestamp(lineup_at, tz=UTC)),
            kind="lineup",
            label="Expected XI news",
        ),
    ]
    timeline = MatchTimeline(
        match_id=match_id, contract="home win", points=points, events=events
    )
    return Envelope(data=timeline, provenance=make_provenance(state.cfg, source="mock"))


_SETTLEMENT_TEXTS = {
    "home_win": (
        "{home} to be declared the winner of the match vs {away} at full time. "
        "Extra time and penalties DO NOT count; a knockout win on penalties settles NO."
    ),
    "over_2_5": (
        "Total goals scored by both teams to exceed 2.5 at full time. "
        "Own goals count; extra-time goals DO NOT count."
    ),
}


def _mock_opportunity_rows(state: ApiState) -> list[MarketOpportunity]:
    """Every board row derives from the SAME match cores the prediction screens
    serve: a fair value here can never contradict Match Detail. The waterfall
    is exact by construction (last value_after == fair.p) and the settlement
    invariant holds: unconfirmed mapping <=> actionability 'Unsafe'."""
    min_edge = state.cfg.risk.min_edge
    rows: list[MarketOpportunity] = []
    for i in range(len(_MOCK_FIXTURES)):
        core = _mock_match_core(state, i)
        fx, ens, unc, half = core["fixture"], core["ens"], core["uncertainty"], core["band_half"]
        for contract, model_p in (("home_win", ens["home"]), ("over_2_5", ens["over_2_5"])):
            label = f"{fx['home']} win" if contract == "home_win" else "Over 2.5 goals"
            event = (
                f"{fx['home'].upper()}_BEATS_{fx['away'].upper()}_FT"
                if contract == "home_win"
                else f"{fx['home'].upper()}_{fx['away'].upper()}_TOTAL_GT_2_5_FT"
            )
            for venue in ("kalshi", "polymarket"):
                import hashlib
                hash_str = f"{state.cfg.seed}-{i}-{contract}-{venue}"
                hash_val = int(hashlib.sha256(hash_str.encode()).hexdigest(), 16) & 0xFFFFFFFF
                rng = random.Random(hash_val)
                fees = -round(rng.uniform(0.008, 0.018), 4)
                timing = -round(rng.uniform(0.001, 0.006), 4)
                resolution = -round(rng.uniform(0.002, 0.010), 4)
                fair_p = model_p + fees + timing + resolution
                steps = [
                    FairValueStep(label="model_probability", delta=model_p, value_after=model_p),
                    FairValueStep(label="fees", delta=fees, value_after=model_p + fees),
                    FairValueStep(label="timing_lockup", delta=timing, value_after=model_p + fees + timing),
                    FairValueStep(label="resolution_risk", delta=resolution, value_after=fair_p),
                ]
                mid = min(0.97, max(0.03, fair_p - rng.uniform(-0.06, 0.06)))
                spread = rng.uniform(0.015, 0.04)
                edge = round(fair_p - mid, 4)
                risk_adj = round(edge * (1 - unc), 4)
                classification = rng.choice(["my-info", "their-info", "settlement-trap", "incoherence"])
                confirmed = classification != "settlement-trap" and rng.random() > 0.15
                stale = rng.random() < 0.08
                if not confirmed:
                    actionability = "Unsafe"
                elif stale:
                    actionability = "Stale"
                elif abs(risk_adj) >= min_edge:
                    actionability = "Tradeable"
                elif abs(risk_adj) > 0.005:
                    actionability = "Watch"
                else:
                    actionability = "No Edge"
                rows.append(
                    MarketOpportunity(
                        venue=venue,
                        ticker=f"{'KX' if venue == 'kalshi' else 'PM'}-WC26-{fx['home'][:3].upper()}{fx['away'][:3].upper()}-{'WIN' if contract == 'home_win' else 'O25'}",
                        contract_label=f"{fx['home']} vs {fx['away']}: {label}",
                        # Full precision: rounding is presentation and belongs
                        # to the UI; rounding here breaks the waterfall's
                        # exact sum-to-fair invariant.
                        fair_value=fair_p,
                        fair=ProbWithBand(
                            p=fair_p,
                            lo=max(0.0, fair_p - half),
                            hi=min(1.0, fair_p + half),
                        ),
                        best_bid=round(mid - spread / 2, 3),
                        best_ask=round(mid + spread / 2, 3),
                        depth_bid=rng.randrange(50, 2500, 10),
                        depth_ask=rng.randrange(50, 2500, 10),
                        edge_after_fees=edge,
                        edge_risk_adjusted=risk_adj,
                        uncertainty_score=round(unc, 3),
                        classification=classification,
                        actionability=actionability,
                        decomposition=steps,
                        settlement=SettlementMapping(
                            market_text=_SETTLEMENT_TEXTS[contract].format(home=fx["home"], away=fx["away"]),
                            model_event=event,
                            confirmed=confirmed,
                            confirmed_at=to_iso(utc_now()) if confirmed else None,
                            note=None if confirmed else "Mapping not human-reviewed: full-time vs extra-time definition unchecked.",
                        ),
                    )
                )
    rows.sort(key=lambda o: abs(o.edge_risk_adjusted), reverse=True)
    return rows


@app.get("/api/v1/opportunities", response_model=Envelope[list[MarketOpportunity]])
def get_opportunities(state: StateDep) -> Envelope[list[MarketOpportunity]]:
    rows = _mock_opportunity_rows(state)
    return Envelope(data=rows, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/coherence", response_model=Envelope[CoherenceReport])
def get_coherence(state: StateDep) -> Envelope[CoherenceReport]:
    """Cross-venue rows come from the SAME opportunity rows the board serves;
    internal rows mock the bracket-path-product vs direct-price check the
    simulator's joint draws will answer for real (ADR-0006's coherence edge)."""
    rows = _mock_opportunity_rows(state)
    by_event: dict[str, dict[str, MarketOpportunity]] = {}
    for r in rows:
        by_event.setdefault(r.contract_label, {})[r.venue] = r

    cross: list[CrossVenueRow] = []
    for event, venues in by_event.items():
        kx = venues.get("kalshi")
        pm = venues.get("polymarket")
        mid = lambda o: round((o.best_bid + o.best_ask) / 2, 4)  # noqa: E731
        ref = kx.fair.p if kx else (pm.fair.p if pm else None)
        prices = [p for p in (mid(kx) if kx else None, mid(pm) if pm else None, ref) if p is not None]
        spread_pp = round((max(prices) - min(prices)) * 100, 2) if len(prices) > 1 else 0.0
        cross.append(
            CrossVenueRow(
                event=event,
                kalshi=mid(kx) if kx else None,
                polymarket=mid(pm) if pm else None,
                devig_ref=ref,
                max_spread_pp=spread_pp,
            )
        )
    cross.sort(key=lambda c: c.max_spread_pp, reverse=True)

    rng = random.Random(state.cfg.seed + 42)
    internal: list[InternalViolation] = []
    for i in range(min(2, len(_MOCK_FIXTURES))):
        core = _mock_match_core(state, i)
        fx = core["fixture"]
        p_group = round(core["ens"]["home"] * rng.uniform(0.55, 0.75), 4)
        p_champ_given = round(rng.uniform(0.15, 0.35), 4)
        product = round(p_group * p_champ_given, 4)
        direct = round(product + rng.uniform(-0.02, 0.02), 4)
        internal.append(
            InternalViolation(
                description=(
                    f"P({fx['home']} wins Group {fx['group']}) x P(champion | wins group) "
                    f"= {p_group} x {p_champ_given} vs direct champion price"
                ),
                product_price=product,
                direct_price=direct,
                gap_pp=round((direct - product) * 100, 2),
                safest_class="incoherence",
            )
        )
    report = CoherenceReport(cross_venue=cross, internal=internal)
    return Envelope(data=report, provenance=make_provenance(state.cfg, source="mock"))


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, state: StateDep) -> None:
    """Multiplexed topic stream; protocol and topics documented in ws.py (ADR-0014)."""
    await serve_ws(websocket, state)


# --- Tournament + joint query (MOCK: counted from the deterministic draw
# table in mock_tournament.py; swaps to the simulator's persisted draws) ----


def _band_from_counts(hits: int, n: int) -> ProbWithBand:
    lo, hi = wilson_ci(hits, n)
    return ProbWithBand(p=hits / n if n else 0.0, lo=lo, hi=hi)


@app.get("/api/v1/tournament", response_model=Envelope[TournamentState])
def get_tournament(state: StateDep) -> Envelope[TournamentState]:
    dt = draw_table(state.cfg.seed)
    n = dt.n_draws

    groups: list[GroupTable] = []
    third_candidates: list[ThirdPlaceCandidate] = []
    for g, letter in enumerate(GROUPS):
        idx = [i for i in range(len(dt.teams)) if dt.group_of[i] == g]
        rows = []
        for i in idx:
            ranks = dt.rank_in_group[:, i]
            third = ranks == 3
            n_third = int(third.sum())
            n_bt = int(dt.best_third[:, i].sum())
            rows.append(
                TeamGroupProbs(
                    team=dt.teams[i],
                    p_first=float((ranks == 1).mean()),
                    p_second=float((ranks == 2).mean()),
                    p_third=float(third.mean()),
                    p_best_third_qualify=n_bt / n,
                    p_advance=float((dt.reached[:, i] >= STAGE_R32).mean()),
                )
            )
            third_candidates.append(
                ThirdPlaceCandidate(
                    team=dt.teams[i],
                    group=letter,
                    p_third=n_third / n,
                    p_qualify_given_third=(n_bt / n_third) if n_third else 0.0,
                    p_best_third_qualify=n_bt / n,
                )
            )
        rows.sort(key=lambda r: r.p_first, reverse=True)
        groups.append(GroupTable(group=letter, teams=rows))

    third_candidates.sort(key=lambda c: c.p_best_third_qualify, reverse=True)

    advancement = [
        AdvancementRow(
            team=dt.teams[i],
            p_r32=float((dt.reached[:, i] >= STAGE_R32).mean()),
            p_r16=float((dt.reached[:, i] >= STAGE_R16).mean()),
            p_qf=float((dt.reached[:, i] >= STAGE_QF).mean()),
            p_sf=float((dt.reached[:, i] >= STAGE_SF).mean()),
            p_final=float((dt.reached[:, i] >= STAGE_FINAL).mean()),
            p_champion=float((dt.reached[:, i] >= STAGE_CHAMPION).mean()),
        )
        for i in range(len(dt.teams))
    ]
    advancement.sort(key=lambda a: a.p_champion, reverse=True)

    winner = [
        WinnerProb(
            team=row.team,
            p=_band_from_counts(int(round(row.p_champion * n)), n),
        )
        for row in advancement[:10]
    ]

    data = TournamentState(
        n_draws=n,
        groups=groups,
        third_place_race=third_candidates[:16],
        advancement=advancement[:16],
        winner=winner,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.post("/api/v1/sim/query", response_model=Envelope[SimQueryResult])
def sim_query(req: SimQueryRequest, state: StateDep) -> Envelope[SimQueryResult]:
    """Joint probability of arbitrary event combinations, COUNTED from the
    persisted draws - never multiplied marginals. The dependence_ratio next to
    the counted joint is the coherence edge made visible (ADR-0006)."""
    dt = draw_table(state.cfg.seed)
    n = dt.n_draws
    try:
        masks = [dt.event_mask(e.team, e.outcome) for e in req.events]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_team", "team": str(exc)}) from exc

    joint = masks[0].copy()
    product = 1.0
    for m in masks:
        product *= float(m.mean())
    for m in masks[1:]:
        joint &= m
    hits = int(joint.sum())
    p = hits / n

    data = SimQueryResult(
        events=req.events,
        p=_band_from_counts(hits, n),
        n_draws=n,
        n_hits=hits,
        independent_product=product,
        dependence_ratio=(p / product) if product > 0 else None,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


# --- Fenced commands (Phase 4): the UI's ONLY write path. REAL ledger writes;
# state is a fold over command entries (api/commands.py) -------------------


def _command_state_out(s: CommandState) -> CommandStateOut:
    return CommandStateOut(
        killed=s.killed,
        killed_at=s.killed_at,
        kill_reason=s.kill_reason,
        paused_tickers=s.paused_tickers,
        widen_factor=s.widen_factor,
    )


def _command_envelope(state: ApiState, result: CommandState, seq: int | None, already: bool) -> Envelope[CommandResult]:
    data = CommandResult(accepted=True, already=already, ledger_seq=seq, state=_command_state_out(result))
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="real"))


@app.get("/api/v1/commands/state", response_model=Envelope[CommandStateOut])
def get_command_state(state: StateDep) -> Envelope[CommandStateOut]:
    s = read_command_state(state)
    return Envelope(data=_command_state_out(s), provenance=make_provenance(state.cfg, source="real"))


@app.post("/api/v1/commands/kill-switch", response_model=Envelope[CommandResult])
def post_kill_switch(req: KillRequest, state: StateDep) -> Envelope[CommandResult]:
    s, seq, already = command_kill(state, req.reason)
    return _command_envelope(state, s, seq, already)


@app.post("/api/v1/commands/quoting/{ticker}/pause", response_model=Envelope[CommandResult])
def post_pause(ticker: str, req: PauseResumeRequest, state: StateDep) -> Envelope[CommandResult]:
    s, seq = command_pause(state, ticker, req.reason)
    return _command_envelope(state, s, seq, already=seq is None)


@app.post("/api/v1/commands/quoting/{ticker}/resume", response_model=Envelope[CommandResult])
def post_resume(ticker: str, req: PauseResumeRequest, state: StateDep) -> Envelope[CommandResult]:
    try:
        s, seq = command_resume(state, ticker, req.reason)
    except CommandRejected as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "detail": exc.detail}) from exc
    return _command_envelope(state, s, seq, already=seq is None)


@app.post("/api/v1/commands/quoting/widen-all", response_model=Envelope[CommandResult])
def post_widen(req: WidenRequest, state: StateDep) -> Envelope[CommandResult]:
    s, seq = command_widen(state, req.factor)
    return _command_envelope(state, s, seq, already=False)


# --- MM Console (MOCK book/fills; REAL quote math via execution.quoting;
# REAL command state) --------------------------------------------------------


def _opportunity_by_ticker(state: ApiState, ticker: str) -> MarketOpportunity:
    for row in _mock_opportunity_rows(state):
        if row.ticker == ticker:
            return row
    raise HTTPException(status_code=404, detail={"code": "unknown_ticker", "ticker": ticker})


def _news_state(state: ApiState, opp: MarketOpportunity) -> str:
    if not opp.settlement.confirmed:
        return "quarantined"
    for i, fx in enumerate(_MOCK_FIXTURES):
        if fx["home"][:3].upper() in opp.ticker:
            core = _mock_match_core(state, i)
            if core["fixture"]["lineup_confirmed"] and fx["kickoff_in_h"] <= 12:
                return "lineup-window"
    return "normal"


@app.get("/api/v1/console/{ticker}", response_model=Envelope[ConsoleState])
def get_console(ticker: str, state: StateDep) -> Envelope[ConsoleState]:
    opp = _opportunity_by_ticker(state, ticker)
    cmd = read_command_state(state)
    rng = random.Random(hash((state.cfg.seed, "console", ticker)) & 0xFFFFFFFF)

    fair = opp.fair.p
    variance = fair * (1 - fair)
    inventory_contracts = rng.randrange(-200, 300, 10)
    # A-S inputs must be scaled for a [0,1] binary asset: inventory in
    # 100-lots (else gamma*var*inv*T shifts the reservation price off the
    # price axis entirely) and an arrival rate that yields a centi-scale
    # spread. gamma=0.5, k=30/day -> base spread ~7c; the engine's defaults
    # (gamma=0.1, k=1.5) produce a 1.29 spread and clamp to nonsense.
    inventory = inventory_contracts / 100.0
    t_days = 0.25
    gamma = 0.5
    fee_floor = 0.012

    # REAL quote math (Avellaneda-Stoikov) on the mock inputs, with the
    # ledgered widen factor applied and the fee floor enforced.
    engine = QuotingEngine(risk_aversion=gamma, arrival_rate=30.0)
    raw_bid, raw_ask = engine.compute_quotes(fair, inventory, variance, t_days)
    half = max((raw_ask - raw_bid) / 2 * cmd.widen_factor, fee_floor / 2)
    r_mid = (raw_bid + raw_ask) / 2
    bid, ask = max(0.01, r_mid - half), min(0.99, r_mid + half)

    paused = ticker in cmd.paused_tickers
    status = "killed" if cmd.killed else ("paused" if paused else "active")
    active = status == "active"

    # Mock ladder around the venue mid, deterministic per ticker.
    mid = (opp.best_bid + opp.best_ask) / 2
    bids = [
        BookLevel(price=round(mid - 0.01 * (k + 1), 3), size=rng.randrange(50, 1500, 10))
        for k in range(5)
    ]
    asks = [
        BookLevel(price=round(mid + 0.01 * (k + 1), 3), size=rng.randrange(50, 1500, 10))
        for k in range(5)
    ]

    contexts = ["normal book", "lineup window open", "goal in parallel match", "spread widened"]
    now_s = utc_now().timestamp()
    fills = [
        Fill(
            ts_utc=to_iso(datetime.fromtimestamp(now_s - k * 1800, tz=UTC)),
            ticker=ticker,
            side=rng.choice(["buy", "sell"]),
            price=round(mid + rng.uniform(-0.02, 0.02), 3),
            size=rng.randrange(10, 200, 10),
            context=rng.choice(contexts),
        )
        for k in range(1, 5)
    ]

    data = ConsoleState(
        ticker=ticker,
        book_bids=bids,
        book_asks=asks,
        book_as_of=to_iso(utc_now()),
        my_quotes=MyQuotes(bid=round(bid, 3), ask=round(ask, 3), size=200, active=active),
        quote_inputs=QuoteInputs(
            fair_value=fair,
            variance=variance,
            inventory=float(inventory_contracts),
            time_to_settlement_days=t_days,
            gamma=gamma,
            fee_floor=fee_floor,
            widen_factor=cmd.widen_factor,
            news_state=_news_state(state, opp),  # type: ignore[arg-type]
            bid=round(bid, 3),
            ask=round(ask, 3),
            spread=round(ask - bid, 4),
            skew=round(r_mid - fair, 4),
        ),
        quoting_status=status,  # type: ignore[arg-type]
        fills=fills,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/portfolio", response_model=Envelope[PortfolioState])
def get_portfolio(state: StateDep) -> Envelope[PortfolioState]:
    """Clusters follow the fixtures (positions in the same match co-move);
    targets come from the REAL convex optimizer on a mock covariance."""
    import numpy as np

    rows = _mock_opportunity_rows(state)
    rng = random.Random(state.cfg.seed + 99)
    clusters: list[PositionCluster] = []
    edges, exposures = [], []
    for i, fx in enumerate(_MOCK_FIXTURES):
        tickers = [r for r in rows if fx["home"][:3].upper() in r.ticker]
        positions = []
        net = 0.0
        for r in tickers:
            qty = rng.randrange(-150, 250, 10)
            mark = (r.best_bid + r.best_ask) / 2
            positions.append(
                ClusterPosition(ticker=r.ticker, qty=qty, avg_price=round(mark - 0.01, 3), mark=round(mark, 3))
            )
            net += qty * mark
        edges.append(abs(sum(r.edge_risk_adjusted for r in tickers)) / max(1, len(tickers)))
        exposures.append(net)
        # Serve internally consistent numbers: utilization derives from the
        # SAME (cent-rounded) exposure the row displays, or the two fields
        # disagree in the client's arithmetic.
        net = round(net, 2)
        clusters.append(
            PositionCluster(
                cluster_id=f"match-{i}",
                label=f"{fx['home']} vs {fx['away']} (Group {fx['group']})",
                net_exposure_usd=net,
                limit_usd=500.0,
                utilization=abs(net) / 500.0,
                optimizer_target_usd=0.0,  # filled below
                positions=positions,
            )
        )

    # REAL optimizer: block covariance (same-cluster positions correlated).
    n = len(clusters)
    cov = np.eye(n) * 0.04 + np.ones((n, n)) * 0.005
    optimizer = PortfolioOptimizer(risk_budget=1500.0, per_event_limit=500.0)
    targets = optimizer.optimize(np.array(edges), cov)
    scale = 1500.0 / max(1e-9, float(np.abs(targets).sum()))
    for c, t in zip(clusters, targets, strict=True):
        c.optimizer_target_usd = round(float(t) * scale, 2)

    data = PortfolioState(
        clusters=clusters,
        total_exposure_usd=round(sum(c.net_exposure_usd for c in clusters), 2),
        risk_budget_usd=1500.0,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


# --- Ops + alerts (Phase 6 core): mock alerts/freshness, REAL ack state ----


def _mock_alerts_raw(state: ApiState) -> list[dict]:
    """Deterministic alert set with STABLE ids (seed-derived, not time-derived)
    so ledgered acks survive restarts and re-reads."""
    rng = random.Random(state.cfg.seed + 7)
    now_s = utc_now().timestamp()
    defs = [
        {
            "kind": "divergence",
            "severity": "critical",
            "age_min": 12,
            "message": (
                "Model vs de-vigged market moved 6.2pp on KX-WC26-USAENG-WIN in 10 minutes. "
                "Check data freshness FIRST: divergence spikes usually mean YOUR data is stale, "
                "not that the market is wrong."
            ),
        },
        {
            "kind": "calibration_drift",
            "severity": "warn",
            "age_min": 95,
            "message": (
                "Rolling 200-sample calibration slope drifted to 0.87 (target 1.0 ± 0.1) on 1X2 markets. "
                "Ensemble may be overconfident; review before widening size."
            ),
        },
        {
            "kind": "stale_source",
            "severity": "warn",
            "age_min": 260,
            "message": "Elo ingest last succeeded 26h ago (max 24h). Ratings-driven features are running on yesterday.",
        },
        {
            "kind": "reconciliation",
            "severity": "info",
            "age_min": 420,
            "message": "Paper-book vs exchange-state reconciliation completed clean on both venues.",
        },
    ]
    alerts = []
    for d in defs:
        stable = f"AL-{d['kind']}-{rng.randrange(10_000, 99_999)}"
        alerts.append(
            {
                **d,
                "alert_id": stable,
                "ts_utc": to_iso(datetime.fromtimestamp(now_s - d["age_min"] * 60, tz=UTC)),
            }
        )
    return alerts


@app.get("/api/v1/alerts", response_model=Envelope[AlertsPage])
def get_alerts(state: StateDep) -> Envelope[AlertsPage]:
    acked = read_command_state(state).acked_alerts
    alerts = [
        Alert(
            alert_id=a["alert_id"],
            ts_utc=a["ts_utc"],
            severity=a["severity"],
            kind=a["kind"],
            message=a["message"],
            acked=a["alert_id"] in acked,
            acked_at=acked.get(a["alert_id"]),
        )
        for a in _mock_alerts_raw(state)
    ]
    alerts.sort(key=lambda a: (a.acked, a.ts_utc), reverse=False)
    data = AlertsPage(alerts=alerts, unacked=sum(1 for a in alerts if not a.acked))
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.post("/api/v1/alerts/{alert_id}/ack", response_model=Envelope[CommandResult])
def post_ack_alert(alert_id: str, state: StateDep) -> Envelope[CommandResult]:
    known = {a["alert_id"] for a in _mock_alerts_raw(state)}
    if alert_id not in known:
        raise HTTPException(status_code=404, detail={"code": "unknown_alert", "alert_id": alert_id})
    s, seq = command_ack_alert(state, alert_id)
    return _command_envelope(state, s, seq, already=seq is None)


@app.get("/api/v1/ops/freshness", response_model=Envelope[OpsFreshness])
def get_ops_freshness(state: StateDep) -> Envelope[OpsFreshness]:
    rng = random.Random(state.cfg.seed + 13)
    now_s = utc_now().timestamp()
    defs = [
        ("kalshi order books", 45, 120),
        ("polymarket order books", 51, 120),
        ("fbref match data", 9_000, 43_200),
        ("elo ratings", 93_600, 86_400),  # deliberately stale in mock
        ("venue / weather", 960, 3_600),
    ]
    sources = []
    for name, age, max_age in defs:
        jitter = rng.uniform(0.9, 1.1)
        staleness = age * jitter
        sources.append(
            FreshnessSource(
                source=name,
                last_success_utc=to_iso(datetime.fromtimestamp(now_s - staleness, tz=UTC)),
                staleness_seconds=staleness,
                max_age_seconds=max_age,
                status="stale" if staleness > max_age else "ok",
            )
        )
    recon = [
        ReconciliationRow(venue="kalshi", status="match", detail="0 position diffs, 0 order diffs (paper)"),
        ReconciliationRow(venue="polymarket", status="match", detail="0 position diffs, 0 order diffs (paper)"),
    ]
    data = OpsFreshness(sources=sources, reconciliation=recon)
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


# --- Evaluation (Phase 5): REAL statistics over the mock resolved table ----


def _ci_value(losses, seed: int) -> CIValue:
    import numpy as np

    arr = np.asarray(losses, dtype=float)
    lo, hi = bootstrap_ci(arr, seed=seed)
    return CIValue(value=float(arr.mean()), ci_lo=lo, ci_hi=hi, n=int(len(arr)))


@app.get("/api/v1/eval/clv", response_model=Envelope[ClvReport])
def get_eval_clv(state: StateDep) -> Envelope[ClvReport]:
    import numpy as np

    t = eval_table(state.cfg.seed)
    clv_pp = (t.close_p - t.entry_p) * 100  # prob points captured vs close

    cumulative = [
        ClvPoint(ts_utc=to_iso(datetime.fromtimestamp(ts, tz=UTC)), cum_pp=float(c))
        for ts, c in zip(t.ts_epoch[::8], np.cumsum(clv_pp)[::8], strict=True)
    ]
    edges = np.linspace(clv_pp.min(), clv_pp.max(), 21)
    counts, _ = np.histogram(clv_pp, bins=edges)
    histogram = [
        ClvHistBin(lo_pp=float(edges[i]), hi_pp=float(edges[i + 1]), count=int(c))
        for i, c in enumerate(counts)
    ]
    by_class = [
        ClvByClass(market_class=mc, mean_pp=_ci_value(clv_pp[t.market_class == mc], seed=state.cfg.seed + i))
        for i, mc in enumerate(MARKET_CLASSES)
    ]
    data = ClvReport(
        mean_pp=_ci_value(clv_pp, seed=state.cfg.seed),
        cumulative=cumulative,
        histogram=histogram,
        by_class=by_class,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/eval/calibration", response_model=Envelope[CalibrationReport])
def get_eval_calibration(
    state: StateDep,
    model: str = Query(default="ensemble"),
) -> Envelope[CalibrationReport]:
    import numpy as np

    t = eval_table(state.cfg.seed)
    if model not in t.model_p:
        raise HTTPException(status_code=404, detail={"code": "unknown_model", "model": model})
    p = t.model_p[model]
    bins = []
    for lo in np.arange(0.0, 1.0, 0.1):
        mask = (p >= lo) & (p < lo + 0.1)
        n = int(mask.sum())
        if n == 0:
            bins.append(CalibrationBin(p_mid=float(lo + 0.05), n=0, empirical=0.0, ci_lo=0.0, ci_hi=1.0))
            continue
        hits = int(t.outcome[mask].sum())
        ci_lo, ci_hi = wilson_ci(hits, n)
        bins.append(
            CalibrationBin(p_mid=float(lo + 0.05), n=n, empirical=hits / n, ci_lo=ci_lo, ci_hi=ci_hi)
        )
    data = CalibrationReport(model=model, n_total=t.n, bins=bins)
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/eval/model-race", response_model=Envelope[ModelRaceReport])
def get_eval_model_race(state: StateDep) -> Envelope[ModelRaceReport]:
    t = eval_table(state.cfg.seed)
    market_ll = pointwise_log_loss(t.outcome, t.market_p)

    current_w = t.weights_over_time[-1]["weights"]
    rows = []
    for i, (name, p) in enumerate(sorted(t.model_p.items())):
        ll = pointwise_log_loss(t.outcome, p)
        br = pointwise_brier(t.outcome, p)
        stat, sig = diebold_mariano(ll, market_ll)
        rows.append(
            RaceRow(
                model=name,
                log_loss=_ci_value(ll, seed=state.cfg.seed + 100 + i),
                brier=_ci_value(br, seed=state.cfg.seed + 200 + i),
                dm_vs_market=stat,
                dm_significant=sig,
                weight=current_w.get(name),
            )
        )
    rows.append(
        RaceRow(
            model="market (de-vig)",
            log_loss=_ci_value(market_ll, seed=state.cfg.seed + 300),
            brier=_ci_value(pointwise_brier(t.outcome, t.market_p), seed=state.cfg.seed + 301),
            dm_vs_market=0.0,
            dm_significant=False,
            weight=None,
        )
    )
    rows.sort(key=lambda r: r.log_loss.value)
    weights_over_time = [
        WeightsPoint(ts_utc=to_iso(datetime.fromtimestamp(w["ts_epoch"], tz=UTC)), weights=w["weights"])
        for w in t.weights_over_time
    ]
    data = ModelRaceReport(n=t.n, rows=rows, weights_over_time=weights_over_time)
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/eval/pnl", response_model=Envelope[PnlReport])
def get_eval_pnl(state: StateDep) -> Envelope[PnlReport]:
    import numpy as np

    t = eval_table(state.cfg.seed)
    # Paper P&L: $1 notional per event on the outcome vs entry price.
    pnl = (t.outcome - t.entry_p) * 1.0
    cum = np.cumsum(pnl)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    points = [
        PnlPoint(
            ts_utc=to_iso(datetime.fromtimestamp(ts, tz=UTC)),
            cum_pnl=float(c),
            drawdown=float(d),
        )
        for ts, c, d in zip(t.ts_epoch[::4], cum[::4], dd[::4], strict=True)
    ]
    data = PnlReport(
        mode=state.cfg.mode,
        n_trades=t.n,
        points=points,
        max_drawdown=float(dd.min()),
        kelly_fraction=0.25,
    )
    return Envelope(data=data, provenance=make_provenance(state.cfg, source="mock"))


# --- Pre-registration gates (REAL: parsed from docs/preregistrations) ------


@app.get("/api/v1/prereg", response_model=Envelope[PreregPage])
def get_prereg(state: StateDep) -> Envelope[PreregPage]:
    """Real files, definitive empty state. The UI renders gates as first-class
    objects so moving a goalpost is visible, not easy."""
    import re

    prereg_dir = state.root / "docs" / "preregistrations"
    gates: list[PreregGate] = []
    if prereg_dir.exists():
        for f in sorted(prereg_dir.glob("*.md")):
            if f.name.startswith("_") or f.name.lower() == "readme.md":
                continue
            text = f.read_text(encoding="utf-8")
            title_m = re.search(r"^# Pre-registration:\s*(.+)$", text, re.M)
            status_m = re.search(r"^- Status:\s*(\S+)", text, re.M)
            frozen_m = re.search(r"^- Date frozen[^:]*:\s*(\S+)", text, re.M)
            metric_m = re.search(r"## Metric\s*\n+([^\n#]+)", text)
            thresh_m = re.search(r"- Threshold[^:]*:\s*(.+)$", text, re.M)
            gates.append(
                PreregGate(
                    gate_id=f.stem,
                    title=title_m.group(1).strip() if title_m else f.stem,
                    status=status_m.group(1).strip() if status_m else "unknown",
                    metric=metric_m.group(1).strip() if metric_m else None,
                    threshold=thresh_m.group(1).strip() if thresh_m else None,
                    frozen_at=frozen_m.group(1).strip() if frozen_m else None,
                    path=str(f.relative_to(state.root)),
                )
            )
    return Envelope(data=PreregPage(gates=gates), provenance=make_provenance(state.cfg, source="real"))
