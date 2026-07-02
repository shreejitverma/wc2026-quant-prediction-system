"""UTC-only timestamp discipline.

Every timestamp in this system is timezone-aware UTC. Naive datetimes are
rejected at the boundary rather than silently assumed to be local time - a
single mislabeled timezone is one of the classic ways a sports backtest leaks
(a lineup "released at 18:00" that was actually 18:00 UTC vs 18:00 local is the
difference between knowable and not-yet-knowable at kickoff).
"""

from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["UTC", "utc_now", "ensure_utc", "to_iso", "from_iso"]


def utc_now() -> datetime:
    """Timezone-aware current time in UTC."""
    return datetime.now(tz=UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Return dt as UTC. Reject naive datetimes loudly.

    We refuse to guess the timezone of a naive datetime: guessing is exactly how
    look-ahead bias sneaks in. Callers must attach tzinfo at the ingest boundary.
    """
    if dt.tzinfo is None:
        raise ValueError(
            "naive datetime rejected: all timestamps must be timezone-aware UTC "
            "(attach tzinfo at the ingest boundary, never here)"
        )
    return dt.astimezone(UTC)


def to_iso(dt: datetime) -> str:
    """Serialize a datetime to a canonical UTC ISO-8601 string."""
    return ensure_utc(dt).isoformat()


def from_iso(s: str) -> datetime:
    """Parse an ISO-8601 string back to a UTC datetime (rejects naive input)."""
    return ensure_utc(datetime.fromisoformat(s))
