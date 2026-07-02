"""Strict, config-driven runtime settings.

All configs are YAML validated by Pydantic with `extra="forbid"`: an unknown or
misspelled key is a hard error, not a silently-ignored no-op. In a system where
a wrong risk limit or a typo'd kill-switch threshold can cost real money, configs
must fail loud.

Two fences are encoded in the type system itself:
  - mode defaults to "paper" (Decision: paper-then-small-live).
  - news.autonomous_trading is Literal[False] - the LLM news pipeline is an
    information router, never an autonomous trading signal (ADR-0009). Setting it
    true in YAML raises a validation error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .hashing import hash_json


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PathsConfig(_Strict):
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    ledger_dir: str = "data/ledger"
    runs_dir: str = "data/runs"


class RiskConfig(_Strict):
    bankroll_usd: float = 5_000.0
    kelly_fraction: float = 0.25  # quarter-Kelly default; justified in Phase 6/7
    max_position_per_event_usd: float = 100.0
    max_portfolio_drawdown_pct: float = 0.20
    min_edge: float = 0.03  # post-fee minimum edge to act; else stay flat


class KillSwitchConfig(_Strict):
    """Hard v1 requirement (user constraint): kill switches are not optional."""

    enabled: bool = True
    max_data_staleness_seconds: int = 120
    pnl_stop_usd: float = 250.0
    reconcile_every_cycle: bool = True


class VenuesConfig(_Strict):
    kalshi_enabled: bool = True
    polymarket_enabled: bool = True
    betfair_enabled: bool = False  # free-first; no funded access yet (ADR-0007)


class NewsConfig(_Strict):
    llm_extraction_enabled: bool = True
    # Type-level fence: the news LLM can never be an autonomous trading signal.
    autonomous_trading: Literal[False] = False
    review_threshold_quote_move: float = 0.02  # facts moving a quote > 2% -> human queue


class AppConfig(_Strict):
    mode: Literal["paper", "live"] = "paper"
    seed: int = 20260611  # WC2026 opening day; fixed default for reproducibility
    paths: PathsConfig = Field(default_factory=PathsConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    kill_switch: KillSwitchConfig = Field(default_factory=KillSwitchConfig)
    venues: VenuesConfig = Field(default_factory=VenuesConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)


def load_config(path: str | Path) -> AppConfig:
    """Load and strictly validate a YAML config file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig.model_validate(data)


def config_hash(cfg: AppConfig) -> str:
    """Stable content hash of a validated config (for run provenance)."""
    return hash_json(cfg.model_dump(mode="json"))
