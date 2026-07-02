"""The point-in-time (leak-proof) access primitive.

Decision 1 of the design made mechanical: there is exactly one way to read a
fact - `as_of(ts)` - and it can only ever return facts whose `knowable_at`
timestamp is <= ts. A feature that depends on data timestamped after the
prediction cutoff is *impossible* to construct through this gate, not merely
discouraged. The Phase 2 feature store is a persistent, typed specialization of
this same contract; the property tests in tests/test_pit.py prove the invariant.

Why this is the foundational primitive: football outcomes are low-scoring
Poisson noise with a genuinely low predictability ceiling, so the apparent skill
injected by even a small leak (a market value scraped "today", a suspension flag
that reflects the card shown *in* the match being predicted) can dwarf the real
signal. Leaks here are the dominant error term, not a minor bias.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .time_utils import ensure_utc


@dataclass(frozen=True)
class PITRecord[T]:
    """A single fact and the instant it became knowable (UTC)."""

    key: str
    knowable_at: datetime
    value: T

    def __post_init__(self) -> None:
        # Normalize to UTC and reject naive timestamps at construction time.
        object.__setattr__(self, "knowable_at", ensure_utc(self.knowable_at))


class PointInTimeStore[T]:
    """In-memory reference implementation of the leak-proof gate.

    The only read path is `as_of`. There is deliberately no method that returns
    all records ignoring time, because such a method is precisely the leak.
    """

    def __init__(self) -> None:
        self._records: list[PITRecord[T]] = []

    def add(self, record: PITRecord[T]) -> None:
        self._records.append(record)

    def add_value(self, key: str, knowable_at: datetime, value: T) -> None:
        self.add(PITRecord(key=key, knowable_at=knowable_at, value=value))

    def as_of(self, ts: datetime, key: str | None = None) -> list[PITRecord[T]]:
        """Facts knowable at or before `ts` (optionally filtered to one key)."""
        ts = ensure_utc(ts)
        out = [r for r in self._records if r.knowable_at <= ts]
        if key is not None:
            out = [r for r in out if r.key == key]
        return out

    def latest(self, ts: datetime, key: str) -> PITRecord[T] | None:
        """The most recent value for `key` that was knowable at `ts`."""
        candidates = self.as_of(ts, key)
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.knowable_at)

    def __len__(self) -> int:
        return len(self._records)
