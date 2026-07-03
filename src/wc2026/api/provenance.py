"""Provenance envelope builder (ADR-0012).

git_commit is cached for the process lifetime: the serving code cannot change
commit mid-process, and shelling out to git per request is waste.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from ..config import AppConfig, config_hash
from ..hashing import git_commit
from ..time_utils import to_iso, utc_now
from .deps import default_root
from .schemas import Provenance


@lru_cache(maxsize=1)
def _serving_commit() -> str | None:
    # Anchor to the repo root, not cwd: launched from elsewhere, cwd has no
    # .git and the provenance would silently read "no-git".
    return git_commit(default_root())


def make_provenance(
    cfg: AppConfig,
    *,
    source: Literal["real", "mock"],
    data_as_of: str | None = None,
    run_id: str | None = None,
) -> Provenance:
    return Provenance(
        source=source,
        generated_at=to_iso(utc_now()),
        data_as_of=data_as_of,
        run_id=run_id,
        git_commit=_serving_commit(),
        config_hash=config_hash(cfg),
    )
