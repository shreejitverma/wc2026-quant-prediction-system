from datetime import UTC, datetime

from wc2026.config import AppConfig
from wc2026.ledger import AppendOnlyLedger
from wc2026.runs import log_run

FIXED_TS = datetime(2026, 6, 11, 18, 0, 0, tzinfo=UTC)


def test_append_increments_and_chains(tmp_path):
    led = AppendOnlyLedger(tmp_path / "ledger.jsonl")
    e0 = led.append("prediction", {"match": "MEX-CAN", "p_home": 0.42}, ts=FIXED_TS)
    e1 = led.append("order", {"contract": "MEX_WIN", "side": "buy", "px": 0.40}, ts=FIXED_TS)
    assert e0["seq"] == 0 and e1["seq"] == 1
    assert e1["prev_hash"] == e0["row_hash"]
    assert led.verify_chain()


def test_reload_continues_chain(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = AppendOnlyLedger(path)
    led.append("prediction", {"a": 1}, ts=FIXED_TS)
    # New handle over the same file must resume seq/hash and stay valid.
    led2 = AppendOnlyLedger(path)
    e = led2.append("prediction", {"a": 2}, ts=FIXED_TS)
    assert e["seq"] == 1
    assert led2.verify_chain()


def test_tamper_is_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = AppendOnlyLedger(path)
    led.append("prediction", {"p_home": 0.42}, ts=FIXED_TS)
    led.append("prediction", {"p_home": 0.55}, ts=FIXED_TS)
    assert led.verify_chain()

    # Edit a historical payload in place (the classic "fix the backtest" move).
    lines = path.read_text().splitlines()
    lines[0] = (
        lines[0]
        .replace('"p_home":0.42', '"p_home":0.99')
        .replace('"p_home": 0.42', '"p_home": 0.99')
    )
    path.write_text("\n".join(lines) + "\n")

    led_after = AppendOnlyLedger(path)
    assert led_after.verify_chain() is False


def test_reproducible_hashes(tmp_path):
    led_a = AppendOnlyLedger(tmp_path / "a.jsonl")
    led_b = AppendOnlyLedger(tmp_path / "b.jsonl")
    payloads = [{"x": 1}, {"y": [1, 2, 3]}, {"z": {"k": "v"}}]
    ha = [led_a.append("k", p, ts=FIXED_TS)["row_hash"] for p in payloads]
    hb = [led_b.append("k", p, ts=FIXED_TS)["row_hash"] for p in payloads]
    assert ha == hb  # identical inputs -> identical chain, bit-for-bit


def test_log_run_writes_valid_record(tmp_path):
    led = AppendOnlyLedger(tmp_path / "runs.jsonl")
    cfg = AppConfig()
    rec = log_run(
        led,
        config=cfg,
        model_name="M1_dixon_coles",
        model_version="0.0.1",
        metrics={"log_loss": 0.98, "brier": 0.21},
        features_hash="deadbeef",
    )
    assert rec.model_name == "M1_dixon_coles"
    assert led.verify_chain()
    entries = led.read_all()
    assert entries[-1]["kind"] == "run"
    assert entries[-1]["payload"]["metrics"]["brier"] == 0.21
