"""Content-addressable hashing and git provenance.

The reproducibility contract for the whole system: any historical prediction,
price, or quote must be re-derivable bit-for-bit. That requires hashing the
inputs that produced it - config, data snapshot, feature matrix - and recording
the git commit. `hash_json` uses a canonical encoding (sorted keys, tight
separators) so that logically-equal objects hash equal regardless of dict
insertion order.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64  # prev_hash of the first ledger entry


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def hash_bytes(b: bytes) -> str:
    return sha256_hex(b)


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON encoding: sorted keys, no incidental whitespace.

    default=str lets us hash datetimes and Paths without special-casing; because
    to_iso() is used everywhere for timestamps, the string form is stable.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def hash_json(obj: Any) -> str:
    """SHA-256 of the canonical JSON encoding of obj."""
    return sha256_hex(canonical_json(obj))


def hash_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Streaming SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(repo: str | Path | None = None) -> str | None:
    """Current HEAD commit, or None if not in a git repo / git unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo) if repo else None,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_dirty(repo: str | Path | None = None) -> bool | None:
    """True if the working tree has uncommitted changes; None if not a repo.

    A dirty tree at fit time is a reproducibility hazard: the recorded commit no
    longer describes the code that ran. Runs record this so it is auditable.
    """
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo) if repo else None,
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
