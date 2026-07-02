"""Append-only, hash-chained, tamper-evident ledger.

Every prediction, price, quote, order, and fill is written here and never
mutated. Two properties matter:

  1. Append-only: entries are only ever added (open in "a" mode, fsync'd). This
     is what makes pre-registration enforceable - you cannot quietly rewrite a
     prediction after seeing the result.
  2. Tamper-evident: each entry stores prev_hash (the previous entry's row_hash)
     and its own row_hash over {seq, ts, kind, prev_hash, payload}. Editing any
     historical entry breaks the chain from that point forward, and
     verify_chain() detects it. This is the difference between a system that
     finds real edge and one that discovers its "edge" was a rewritten backtest
     after money is lost.

Storage is newline-delimited JSON (JSONL), not Parquet. Parquet files are
immutable columnar blobs - appending a single row means rewriting a file, which
is the opposite of what an audit log wants. JSONL appends a line at the OS level
and is trivially inspectable. The *processed data* layer (Phase 1) uses Parquet;
the *audit ledger* uses JSONL. DuckDB reads both. See ADR-0004.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .hashing import GENESIS_HASH, hash_json
from .time_utils import ensure_utc, to_iso, utc_now

# Fields covered by the chain hash, in a fixed logical set (order-independent
# because hash_json sorts keys).
_CORE_FIELDS = ("seq", "ts_utc", "kind", "prev_hash", "payload")


class AppendOnlyLedger:
    """A single JSONL audit log with a per-row hash chain."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq, self._last_hash = self._load_head()

    def _load_head(self) -> tuple[int, str]:
        if not self.path.exists():
            return -1, GENESIS_HASH
        last: dict[str, Any] | None = None
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        if last is None:
            return -1, GENESIS_HASH
        return int(last["seq"]), str(last["row_hash"])

    def append(self, kind: str, payload: Any, ts: datetime | None = None) -> dict[str, Any]:
        """Append one entry and return it (including its computed row_hash)."""
        ts_utc = ensure_utc(ts) if ts is not None else utc_now()
        seq = self._seq + 1
        core = {
            "seq": seq,
            "ts_utc": to_iso(ts_utc),
            "kind": kind,
            "prev_hash": self._last_hash,
            "payload": payload,
        }
        row_hash = hash_json(core)
        entry = {**core, "row_hash": row_hash}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._seq = seq
        self._last_hash = row_hash
        return entry

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def verify_chain(self) -> bool:
        """Recompute the chain from genesis; False if seq gap, break, or edit."""
        prev = GENESIS_HASH
        expected_seq = 0
        for e in self.read_all():
            if int(e["seq"]) != expected_seq:
                return False
            if e["prev_hash"] != prev:
                return False
            core = {k: e[k] for k in _CORE_FIELDS}
            if hash_json(core) != e["row_hash"]:
                return False
            prev = e["row_hash"]
            expected_seq += 1
        return True

    def __len__(self) -> int:
        return self._seq + 1
