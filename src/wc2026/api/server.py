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
from datetime import datetime, timezone
import random
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from ..ledger import AppendOnlyLedger
from ..time_utils import from_iso, to_iso, utc_now
from .deps import ApiState, get_state
from .provenance import make_provenance
from .schemas import (
    Attribution,
    Envelope,
    HealthData,
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
    ProbWithBand,
    RunOut,
    RunsPage,
    TimelineEvent,
    TimelinePoint,
    VenueInfo,
    VenueStatus,
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
        kickoff_utc=to_iso(datetime.fromtimestamp(kickoff, tz=timezone.utc)),
        venue=fx["venue"],
        rest_days_home=fx["rest_home"],
        rest_days_away=fx["rest_away"],
        lineup=LineupStatus(
            state="confirmed" if fx["lineup_confirmed"] else "expected",
            as_of=now_iso,
            confirmed_at=to_iso(datetime.fromtimestamp(now.timestamp() - 40 * 60, tz=timezone.utc))
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
            as_of=to_iso(datetime.fromtimestamp(now.timestamp() - 15 * 60, tz=timezone.utc)),
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
                ts_utc=to_iso(datetime.fromtimestamp(t, tz=timezone.utc)),
                market=round(min(0.99, max(0.01, market)), 4),
                fair=round(fair, 4),
                lo=round(max(0.0, fair - half), 4),
                hi=round(min(1.0, fair + half), 4),
            )
        )
    events = [
        TimelineEvent(
            ts_utc=to_iso(datetime.fromtimestamp(now_s - 30 * 3600, tz=timezone.utc)),
            kind="news",
            label="Keeper fitness doubt reported",
        ),
        TimelineEvent(
            ts_utc=to_iso(datetime.fromtimestamp(lineup_at, tz=timezone.utc)),
            kind="lineup",
            label="Expected XI news",
        ),
    ]
    timeline = MatchTimeline(
        match_id=match_id, contract="home win", points=points, events=events
    )
    return Envelope(data=timeline, provenance=make_provenance(state.cfg, source="mock"))


@app.get("/api/v1/opportunities", response_model=Envelope[list[MarketOpportunity]])
def get_opportunities(state: StateDep) -> Envelope[list[MarketOpportunity]]:
    rng = random.Random(state.cfg.seed + 1)
    min_edge = state.cfg.risk.min_edge  # mock honors the real stay-flat fence
    opportunities = []
    for i in range(10):
        fv = round(rng.uniform(0.1, 0.9), 3)
        edge = round(rng.uniform(-0.05, 0.1), 3)
        opportunities.append(
            MarketOpportunity(
                venue=rng.choice(["kalshi", "polymarket"]),
                ticker=f"MOCK-WC2026-M{i}-WIN",
                fair_value=fv,
                best_bid=round(fv - 0.02, 3),
                best_ask=round(fv + 0.02, 3),
                edge_after_fees=edge,
                actionability="Tradeable" if edge > min_edge else ("Watch" if edge > 0 else "No Edge"),
            )
        )
    opportunities.sort(key=lambda o: o.edge_after_fees, reverse=True)
    return Envelope(data=opportunities, provenance=make_provenance(state.cfg, source="mock"))


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, state: StateDep) -> None:
    """Multiplexed topic stream; protocol and topics documented in ws.py (ADR-0014)."""
    await serve_ws(websocket, state)
