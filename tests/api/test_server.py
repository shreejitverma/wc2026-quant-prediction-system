"""API layer tests: envelope discipline, real reads, definitive empty states.

The contract under test (ADR-0012):
  - every response is Envelope[T] with a provenance block;
  - real endpoints read the same JSONL artifacts the CLI writes;
  - mock endpoints label themselves source="mock";
  - empty is a definitive answer (0 entries), never an error.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wc2026.api.deps import ApiState, get_state
from wc2026.api.server import app
from wc2026.config import AppConfig
from wc2026.ledger import AppendOnlyLedger
from wc2026.runs import log_run

KICKOFF = datetime(2026, 6, 11, 18, 0, 0, tzinfo=UTC)


@pytest.fixture
def state(tmp_path: Path) -> ApiState:
    return ApiState(cfg=AppConfig(), root=tmp_path)


@pytest.fixture
def client(state: ApiState) -> TestClient:
    app.dependency_overrides[get_state] = lambda: state
    yield TestClient(app)
    app.dependency_overrides.clear()


def _envelope(body: dict) -> dict:
    assert set(body) == {"data", "provenance"}
    prov = body["provenance"]
    assert prov["source"] in ("real", "mock")
    assert prov["generated_at"].endswith("+00:00") or prov["generated_at"].endswith("Z")
    assert prov["config_hash"]
    return body


def test_health_empty_state_is_definitive(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/health").json())
    assert body["provenance"]["source"] == "real"
    data = body["data"]
    assert data["mode"] == "paper"  # config fence: paper is the default
    assert data["data_status"] == "empty"
    assert data["ledger_entries"] == 0
    assert data["last_ledger_ts_utc"] is None


def test_ledger_empty_returns_zero_not_error(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/ledger").json())
    assert body["data"] == {
        "entries": [],
        "total_entries": 0,
        "returned": 0,
        "has_more": False,
    }
    assert body["provenance"]["data_as_of"] is None


def test_ledger_read_filter_paginate(client: TestClient, state: ApiState) -> None:
    led = AppendOnlyLedger(state.ledger_path)
    led.append("prediction", {"match": "MEX-CAN", "p_home": 0.42}, ts=KICKOFF)
    led.append("quote", {"contract": "MEX_WIN", "bid": 0.40, "ask": 0.44}, ts=KICKOFF)
    led.append("prediction", {"match": "USA-ENG", "p_home": 0.31}, ts=KICKOFF)

    body = _envelope(client.get("/api/v1/ledger").json())
    assert body["data"]["total_entries"] == 3
    assert [e["seq"] for e in body["data"]["entries"]] == [0, 1, 2]
    assert body["provenance"]["data_as_of"] == body["data"]["entries"][-1]["ts_utc"]

    only_pred = client.get("/api/v1/ledger", params={"kind": "prediction"}).json()
    assert [e["seq"] for e in only_pred["data"]["entries"]] == [0, 2]

    page = client.get("/api/v1/ledger", params={"after_seq": 0, "limit": 1}).json()
    assert [e["seq"] for e in page["data"]["entries"]] == [1]
    assert page["data"]["has_more"] is True


def test_ledger_verify_detects_tampering(client: TestClient, state: ApiState) -> None:
    led = AppendOnlyLedger(state.ledger_path)
    led.append("prediction", {"p": 0.5}, ts=KICKOFF)
    assert client.get("/api/v1/ledger/verify").json()["data"]["valid"] is True

    text = state.ledger_path.read_text()
    state.ledger_path.write_text(text.replace("0.5", "0.9"))  # rewrite history
    assert client.get("/api/v1/ledger/verify").json()["data"]["valid"] is False


def test_runs_roundtrip_and_404(client: TestClient, state: ApiState) -> None:
    rec = log_run(
        AppendOnlyLedger(state.runs_path),
        config=state.cfg,
        model_name="dixon_coles",
        model_version="1.0.0",
        metrics={"log_loss": 0.54},
        notes="test run",
    )

    body = _envelope(client.get("/api/v1/runs").json())
    assert body["data"]["total_runs"] == 1
    run = body["data"]["runs"][0]
    assert run["run_id"] == rec.run_id
    assert run["metrics"] == {"log_loss": 0.54}
    assert run["config_hash"] == rec.config_hash

    detail = client.get(f"/api/v1/runs/{rec.run_id}").json()
    assert detail["provenance"]["run_id"] == rec.run_id

    missing = client.get("/api/v1/runs/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "run_not_found"


def test_mock_endpoints_are_labeled_and_coherent(client: TestClient) -> None:
    matches = _envelope(client.get("/api/v1/matches").json())
    assert matches["provenance"]["source"] == "mock"
    for m in matches["data"]:
        assert m["match_id"].startswith("MOCK_")
        total = m["prob_home_win"] + m["prob_draw"] + m["prob_away_win"]
        assert total == pytest.approx(1.0, abs=1e-9)
        matrix_sum = sum(sum(row) for row in m["scoreline_matrix"])
        assert matrix_sum == pytest.approx(1.0, abs=1e-9)

    opps = _envelope(client.get("/api/v1/opportunities").json())
    assert opps["provenance"]["source"] == "mock"
    min_edge = AppConfig().risk.min_edge
    for o in opps["data"]:
        if o["actionability"] == "Tradeable":
            assert o["edge_after_fees"] > min_edge  # mock honors the stay-flat fence


def test_ws_subscribe_snapshots(client: TestClient, state: ApiState) -> None:
    AppendOnlyLedger(state.ledger_path).append("prediction", {"p": 0.5}, ts=KICKOFF)
    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_json({"subscribe": ["health", "book.MOCK-X"]})
        msgs = [ws.receive_json(), ws.receive_json()]

    by_topic = {m["topic"]: m for m in msgs}
    assert set(by_topic) == {"health", "book.MOCK-X"}

    health = by_topic["health"]
    assert health["source"] == "real"
    assert health["data"]["data"]["ledger_entries"] == 1  # same Envelope as REST
    assert health["data"]["provenance"]["source"] == "real"

    book = by_topic["book.MOCK-X"]
    assert book["source"] == "mock"
    assert len(book["data"]["bids"]) == 5


def test_ws_ledger_backfill_from_seq(client: TestClient, state: ApiState) -> None:
    led = AppendOnlyLedger(state.ledger_path)
    led.append("prediction", {"p": 0.4}, ts=KICKOFF)
    led.append("quote", {"bid": 0.40}, ts=KICKOFF)
    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_json({"subscribe": ["ledger"], "after_seq": -1})
        msg = ws.receive_json()

    assert msg["topic"] == "ledger"
    assert msg["source"] == "real"
    assert [e["seq"] for e in msg["data"]["entries"]] == [0, 1]


def test_mock_is_deterministic(client: TestClient) -> None:
    a = client.get("/api/v1/matches").json()["data"]
    b = client.get("/api/v1/matches").json()["data"]
    assert [m["expected_goals_home"] for m in a] == [m["expected_goals_home"] for m in b]


# --- Phase 2/3: match detail, timeline, opportunity board, coherence --------


def test_match_detail_is_coherent_with_list(client: TestClient) -> None:
    listed = _envelope(client.get("/api/v1/matches").json())["data"][0]
    body = _envelope(client.get(f"/api/v1/matches/{listed['match_id']}").json())
    assert body["provenance"]["source"] == "mock"
    d = body["data"]
    # List and detail must agree: same generator by construction.
    assert abs(d["prob_home_win"]["p"] - listed["prob_home_win"]) < 1e-12
    # Every headline probability is derived from the served matrix.
    m = d["scoreline_matrix"]
    n = len(m)
    p_home = sum(m[h][a] for h in range(n) for a in range(n) if h > a)
    assert abs(p_home - d["prob_home_win"]["p"]) < 1e-12
    # Bands are ordered; weights sum to 1; why[] accounts for the whole gap.
    assert d["prob_home_win"]["lo"] <= d["prob_home_win"]["p"] <= d["prob_home_win"]["hi"]
    assert abs(sum(x["weight"] for x in d["models"]) - 1.0) < 1e-9
    gap_pp = abs(d["ensemble"]["p_home"] - d["market"]["p_home"]) * 100
    assert abs(sum(x["delta_pp"] for x in d["why"]) - gap_pp) < 0.02


def test_match_detail_404(client: TestClient) -> None:
    assert client.get("/api/v1/matches/NOPE").status_code == 404
    assert client.get("/api/v1/matches/MOCK_M99/timeline").status_code == 404


def test_timeline_band_ordering(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/matches/MOCK_M0/timeline").json())
    pts = body["data"]["points"]
    assert len(pts) == 49
    assert all(p["lo"] <= p["fair"] <= p["hi"] for p in pts)
    assert body["data"]["events"], "timeline without event markers is unexplainable"


def test_opportunities_waterfall_and_quarantine_invariants(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/opportunities").json())
    rows = body["data"]
    assert rows
    ranked = [abs(r["edge_risk_adjusted"]) for r in rows]
    assert ranked == sorted(ranked, reverse=True), "board must arrive ranked"
    for r in rows:
        # The waterfall accounts for the whole fair value, exactly.
        assert abs(r["decomposition"][-1]["value_after"] - r["fair"]["p"]) < 1e-9
        walk = 0.0
        for step in r["decomposition"]:
            walk += step["delta"]
            assert abs(walk - step["value_after"]) < 1e-9
        # Unconfirmed settlement mapping <=> quarantined row.
        assert (not r["settlement"]["confirmed"]) == (r["actionability"] == "Unsafe")
        assert r["fair"]["lo"] <= r["fair"]["p"] <= r["fair"]["hi"]


def test_coherence_report_shapes(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/coherence").json())
    data = body["data"]
    assert body["provenance"]["source"] == "mock"
    assert data["cross_venue"], "cross-venue table must not be silently empty"
    spreads = [c["max_spread_pp"] for c in data["cross_venue"]]
    assert spreads == sorted(spreads, reverse=True)
    for v in data["internal"]:
        assert abs((v["direct_price"] - v["product_price"]) * 100 - v["gap_pp"]) < 0.01


# --- Tournament + joint query (counted from the mock draw table) -------------


def test_tournament_counted_invariants(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/tournament").json())
    assert body["provenance"]["source"] == "mock"
    d = body["data"]
    assert d["n_draws"] > 0
    assert len(d["groups"]) == 12
    for g in d["groups"]:
        assert len(g["teams"]) == 4
        # Positions partition the group: each team's 1st/2nd/3rd/4th sums to 1.
        for t in g["teams"]:
            p4 = 1 - t["p_first"] - t["p_second"] - t["p_third"]
            assert -1e-9 <= p4 <= 1
            # advance = top2 + best-third path, so p_advance >= p1+p2 and
            # the best-third contribution never exceeds p_third.
            assert t["p_advance"] >= t["p_first"] + t["p_second"] - 1e-9
            assert t["p_best_third_qualify"] <= t["p_third"] + 1e-9
        # Exactly one group winner per draw: p_first sums to 1 within a group.
        assert abs(sum(t["p_first"] for t in g["teams"]) - 1) < 1e-9
    # Winner bands are ordered and counted.
    for w in d["winner"]:
        assert w["p"]["lo"] <= w["p"]["p"] <= w["p"]["hi"]
    # Advancement rows are monotonically non-increasing across rounds.
    for a in d["advancement"]:
        seq = [a["p_r32"], a["p_r16"], a["p_qf"], a["p_sf"], a["p_final"], a["p_champion"]]
        assert all(x >= y - 1e-9 for x, y in zip(seq, seq[1:]))


def test_sim_query_joint_leq_marginals(client: TestClient) -> None:
    q = {
        "events": [
            {"team": "Brazil", "outcome": "wins_group"},
            {"team": "France", "outcome": "reaches_final"},
        ]
    }
    body = _envelope(client.post("/api/v1/sim/query", json=q).json())
    r = body["data"]
    # Joint counted from draws can never exceed either marginal.
    for ev in q["events"]:
        single = _envelope(
            client.post("/api/v1/sim/query", json={"events": [ev]}).json()
        )["data"]
        assert r["p"]["p"] <= single["p"]["p"] + 1e-9
    assert r["n_hits"] == round(r["p"]["p"] * r["n_draws"])
    assert r["p"]["lo"] <= r["p"]["p"] <= r["p"]["hi"]
    # dependence ratio consistent with its parts
    assert abs(r["dependence_ratio"] * r["independent_product"] - r["p"]["p"]) < 1e-9


def test_sim_query_unknown_team_404(client: TestClient) -> None:
    q = {"events": [{"team": "Narnia", "outcome": "champion"}]}
    assert client.post("/api/v1/sim/query", json=q).status_code == 404


# --- Phase 4: fenced commands (REAL ledger writes) + console -----------------


def test_kill_switch_is_idempotent_and_ledgered(client: TestClient, state: ApiState) -> None:
    r1 = _envelope(client.post("/api/v1/commands/kill-switch", json={"reason": "test kill"}).json())
    assert r1["provenance"]["source"] == "real"
    assert r1["data"]["accepted"] and not r1["data"]["already"]
    seq = r1["data"]["ledger_seq"]
    assert seq is not None
    # Second kill: idempotent - accepted, already, NO new ledger entry.
    r2 = _envelope(client.post("/api/v1/commands/kill-switch", json={"reason": "again"}).json())
    assert r2["data"]["already"] and r2["data"]["ledger_seq"] is None
    entries = AppendOnlyLedger(state.ledger_path).read_all()
    assert sum(1 for e in entries if e["kind"] == "command") == 1
    # The command is in the hash chain and health screams.
    assert AppendOnlyLedger(state.ledger_path).verify_chain()
    health = _envelope(client.get("/api/v1/health").json())["data"]
    assert health["killed"] is True


def test_resume_refused_while_killed(client: TestClient) -> None:
    client.post("/api/v1/commands/quoting/T1/pause", json={})
    client.post("/api/v1/commands/kill-switch", json={"reason": "fence test"})
    r = client.post("/api/v1/commands/quoting/T1/resume", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "killed"


def test_pause_resume_fold_and_idempotence(client: TestClient, state: ApiState) -> None:
    t = "KX-TEST"
    r1 = _envelope(client.post(f"/api/v1/commands/quoting/{t}/pause", json={}).json())["data"]
    assert not r1["already"] and t in r1["state"]["paused_tickers"]
    r2 = _envelope(client.post(f"/api/v1/commands/quoting/{t}/pause", json={}).json())["data"]
    assert r2["already"] and r2["ledger_seq"] is None
    r3 = _envelope(client.post(f"/api/v1/commands/quoting/{t}/resume", json={}).json())["data"]
    assert not r3["already"] and t not in r3["state"]["paused_tickers"]
    # State is a fold over the ledger: a fresh read reproduces it (restart-safe).
    s = _envelope(client.get("/api/v1/commands/state").json())["data"]
    assert s["paused_tickers"] == {}
    assert sum(1 for e in AppendOnlyLedger(state.ledger_path).read_all() if e["kind"] == "command") == 2


def test_widen_factor_clamped(client: TestClient) -> None:
    r = _envelope(client.post("/api/v1/commands/quoting/widen-all", json={"factor": 99}).json())["data"]
    assert r["state"]["widen_factor"] == 3.0


def test_console_quotes_real_engine_and_status(client: TestClient) -> None:
    ticker = _envelope(client.get("/api/v1/opportunities").json())["data"][0]["ticker"]
    body = _envelope(client.get(f"/api/v1/console/{ticker}").json())
    c = body["data"]
    q = c["quote_inputs"]
    assert 0.01 <= q["bid"] < q["ask"] <= 0.99
    assert q["spread"] >= q["fee_floor"] - 1e-9  # fee floor enforced
    assert c["quoting_status"] == "active" and c["my_quotes"]["active"]
    # Pause pulls the console's quotes.
    client.post(f"/api/v1/commands/quoting/{ticker}/pause", json={})
    c2 = _envelope(client.get(f"/api/v1/console/{ticker}").json())["data"]
    assert c2["quoting_status"] == "paused" and not c2["my_quotes"]["active"]
    # Widen-all widens the spread.
    client.post("/api/v1/commands/quoting/widen-all", json={"factor": 2.0})
    c3 = _envelope(client.get(f"/api/v1/console/{ticker}").json())["data"]
    assert c3["quote_inputs"]["spread"] > q["spread"]
    assert client.get("/api/v1/console/NOPE").status_code == 404


def test_portfolio_clusters(client: TestClient) -> None:
    body = _envelope(client.get("/api/v1/portfolio").json())
    p = body["data"]
    assert p["clusters"]
    for c in p["clusters"]:
        assert abs(c["utilization"] - abs(c["net_exposure_usd"]) / c["limit_usd"]) < 1e-6
    assert abs(p["total_exposure_usd"] - sum(c["net_exposure_usd"] for c in p["clusters"])) < 1e-6
