"""Reproducible experiment/run records.

Every model fit or evaluation records enough to re-derive it bit-for-bit: the
git commit, whether the tree was dirty, and content hashes of the config, data
snapshot, and feature matrix that fed it - plus the metrics it produced. Runs
are written to an AppendOnlyLedger so the experiment history is itself immutable
and tamper-evident.

Why a local runs ledger and not MLflow/W&B (ADR-0003): a solo operator needs
provenance and reproducibility, not a tracking server, artifact store, or UI to
babysit. hash-everything + the append-only ledger delivers the property that
actually matters (any historical result is re-derivable and un-rewritable) with
zero infrastructure. MLflow is a clean upgrade point later if a UI is wanted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from .hashing import git_commit, git_dirty, hash_json
from .ledger import AppendOnlyLedger
from .time_utils import to_iso, utc_now


@dataclass
class RunRecord:
    run_id: str
    created_at: str
    git_commit: str | None
    git_dirty: bool | None
    config_hash: str
    data_snapshot_hash: str | None
    features_hash: str | None
    model_name: str
    model_version: str
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


def log_run(
    ledger: AppendOnlyLedger,
    *,
    config: Any,
    model_name: str,
    model_version: str,
    metrics: dict[str, Any],
    data_snapshot_hash: str | None = None,
    features_hash: str | None = None,
    notes: str = "",
    repo: str | Path | None = None,
) -> RunRecord:
    """Create a RunRecord, append it to the runs ledger, and return it.

    `config` may be a dict or any object exposing `.model_dump()` (e.g. an
    AppConfig); it is hashed canonically so the exact configuration is auditable.
    """
    config_dict = config.model_dump(mode="json") if hasattr(config, "model_dump") else config
    rec = RunRecord(
        run_id=uuid4().hex,
        created_at=to_iso(utc_now()),
        git_commit=git_commit(repo),
        git_dirty=git_dirty(repo),
        config_hash=hash_json(config_dict),
        data_snapshot_hash=data_snapshot_hash,
        features_hash=features_hash,
        model_name=model_name,
        model_version=model_version,
        metrics=metrics,
        notes=notes,
    )
    ledger.append(kind="run", payload=asdict(rec))
    return rec
