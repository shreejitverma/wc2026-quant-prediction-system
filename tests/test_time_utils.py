from datetime import UTC, datetime, timedelta, timezone

import pytest

from wc2026.time_utils import ensure_utc, from_iso, to_iso, utc_now


def test_utc_now_is_aware():
    assert utc_now().tzinfo is not None


def test_ensure_utc_rejects_naive():
    with pytest.raises(ValueError):
        ensure_utc(datetime(2026, 6, 11, 18, 0, 0))  # naive -> rejected


def test_ensure_utc_converts_offset():
    ny = timezone(timedelta(hours=-4))
    dt = datetime(2026, 6, 11, 14, 0, 0, tzinfo=ny)
    got = ensure_utc(dt)
    assert got.tzinfo == UTC
    assert got.hour == 18  # 14:00 -04:00 == 18:00 UTC


def test_iso_roundtrip():
    dt = datetime(2026, 7, 19, 15, 0, 0, tzinfo=UTC)
    assert from_iso(to_iso(dt)) == dt
