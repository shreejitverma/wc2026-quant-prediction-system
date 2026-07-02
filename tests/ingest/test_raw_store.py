"""Tests for the RawStore and idempotency contract."""

from datetime import UTC, datetime

from wc2026.ingest.base import RawStore

_DT = datetime(2026, 6, 11, tzinfo=UTC)


def test_write_and_read(tmp_path):
    store = RawStore(tmp_path / "raw")
    p = store.write("kalshi", "test.json", b'{"a":1}', dt=_DT, url="http://example.com")
    assert p.exists()
    assert store.read("kalshi", "test.json", _DT) == b'{"a":1}'


def test_write_is_idempotent(tmp_path):
    store = RawStore(tmp_path / "raw")
    store.write("kalshi", "test.json", b"v1", dt=_DT)
    store.write("kalshi", "test.json", b"v2", dt=_DT)  # should be no-op
    assert store.read("kalshi", "test.json", _DT) == b"v1"


def test_overwrite_flag(tmp_path):
    store = RawStore(tmp_path / "raw")
    store.write("kalshi", "test.json", b"v1", dt=_DT)
    store.write("kalshi", "test.json", b"v2", dt=_DT, overwrite=True)
    assert store.read("kalshi", "test.json", _DT) == b"v2"


def test_meta_written(tmp_path):
    store = RawStore(tmp_path / "raw")
    store.write("kalshi", "test.json", b"x", dt=_DT, url="http://test.com/x")
    meta = store.meta("kalshi", "test.json", _DT)
    assert meta["url"] == "http://test.com/x"
    assert "fetched_utc" in meta


def test_exists(tmp_path):
    store = RawStore(tmp_path / "raw")
    assert not store.exists("kalshi", "test.json", _DT)
    store.write("kalshi", "test.json", b"x", dt=_DT)
    assert store.exists("kalshi", "test.json", _DT)


def test_list_dates(tmp_path):
    store = RawStore(tmp_path / "raw")
    dt1 = datetime(2026, 6, 11, tzinfo=UTC)
    dt2 = datetime(2026, 6, 12, tzinfo=UTC)
    store.write("kalshi", "a.json", b"x", dt=dt1)
    store.write("kalshi", "b.json", b"y", dt=dt2)
    dates = store.list_dates("kalshi")
    assert dates == ["2026-06-11", "2026-06-12"]


def test_text_roundtrip(tmp_path):
    store = RawStore(tmp_path / "raw")
    store.write("results", "results.csv", "date,home,away\n2026-06-11,A,B", dt=_DT)
    assert "2026-06-11" in store.read_text("results", "results.csv", _DT)
