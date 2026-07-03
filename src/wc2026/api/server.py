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
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from ..ledger import AppendOnlyLedger
from ..time_utils import from_iso, to_iso, utc_now
from .deps import ApiState, get_state
from .provenance import make_provenance
from .schemas import (
    Envelope,
    HealthData,
    LedgerEntry,
    LedgerPage,
    LedgerVerification,
    MarketOpportunity,
    MatchPrediction,
    RunOut,
    RunsPage,
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


_MOCK_FIXTURES = [("USA", "England"), ("Brazil", "Argentina"), ("France", "Spain")]


@app.get("/api/v1/matches", response_model=Envelope[list[MatchPrediction]])
def get_matches(state: StateDep) -> Envelope[list[MatchPrediction]]:
    rng = random.Random(state.cfg.seed)  # deterministic: same mock every request
    now_iso = to_iso(utc_now())
    matches = []
    for i, (home, away) in enumerate(_MOCK_FIXTURES):
        lam_h = round(rng.uniform(0.8, 2.4), 2)
        lam_a = round(rng.uniform(0.6, 2.0), 2)
        m = _mock_scorelines(lam_h, lam_a)
        p_home = sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h > a)
        p_draw = sum(m[k][k] for k in range(len(m)))
        matches.append(
            MatchPrediction(
                match_id=f"MOCK_M{i}",
                home_team=home,
                away_team=away,
                expected_goals_home=lam_h,
                expected_goals_away=lam_a,
                prob_home_win=p_home,
                prob_draw=p_draw,
                prob_away_win=1.0 - p_home - p_draw,
                scoreline_matrix=m,
                uncertainty_score=rng.uniform(0.2, 0.8),
                freshness_utc=now_iso,
            )
        )
    return Envelope(data=matches, provenance=make_provenance(state.cfg, source="mock"))


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
