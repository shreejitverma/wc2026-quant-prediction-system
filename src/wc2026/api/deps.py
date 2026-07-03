"""FastAPI dependencies: config and data-root resolution.

The API is a read-mostly client of the same JSONL/Parquet artifacts the CLI
writes (data/ledger, data/runs). Paths resolve exactly like the CLI: relative
to the repo root (override with WC2026_ROOT), through the strict AppConfig
(override with WC2026_CONFIG). Tests override get_state() with a temp root;
nothing in the API layer hardcodes a path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..config import AppConfig, load_config


@dataclass(frozen=True)
class ApiState:
    cfg: AppConfig
    root: Path

    @property
    def ledger_path(self) -> Path:
        return self.root / self.cfg.paths.ledger_dir / "ledger.jsonl"

    @property
    def runs_path(self) -> Path:
        return self.root / self.cfg.paths.runs_dir / "runs.jsonl"


def default_root() -> Path:
    """Repo root from the package location (src layout, uv editable install):
    .../repo/src/wc2026/api/deps.py -> repo. Anchoring to cwd instead means the
    API silently reads/creates a different data/ tree depending on where it was
    launched from - a wrong-ledger bug, not an inconvenience."""
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "pyproject.toml").exists():
        return candidate
    return Path.cwd()


def get_state() -> ApiState:
    root = Path(os.environ.get("WC2026_ROOT") or default_root()).resolve()
    cfg_path = Path(os.environ.get("WC2026_CONFIG", str(root / "configs" / "default.yaml")))
    cfg = load_config(cfg_path) if cfg_path.exists() else AppConfig()
    return ApiState(cfg=cfg, root=root)
