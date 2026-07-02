from pathlib import Path

import pytest
from pydantic import ValidationError

from wc2026.config import AppConfig, config_hash, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_default_config():
    src = REPO_ROOT / "configs" / "default.yaml"
    cfg = load_config(src)
    assert cfg.mode == "paper"
    assert cfg.kill_switch.enabled is True
    assert cfg.venues.betfair_enabled is False


def test_unknown_key_is_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("mode: paper\nrisk:\n  kelly_fration: 0.25\n")  # typo'd key
    with pytest.raises(ValidationError):
        load_config(p)


def test_autonomous_trading_fence(tmp_path):
    p = tmp_path / "danger.yaml"
    p.write_text("news:\n  autonomous_trading: true\n")
    with pytest.raises(ValidationError):
        load_config(p)


def test_config_hash_is_stable_and_sensitive():
    a = AppConfig()
    b = AppConfig()
    assert config_hash(a) == config_hash(b)
    c = AppConfig.model_validate({"risk": {"kelly_fraction": 0.5}})
    assert config_hash(c) != config_hash(a)


def test_live_mode_is_allowed_but_not_default():
    cfg = AppConfig.model_validate({"mode": "live"})
    assert cfg.mode == "live"
    assert AppConfig().mode == "paper"


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"mode": "yolo"})
