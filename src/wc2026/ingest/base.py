"""Raw store + polite HTTP client.

Two primitives that every ingest module builds on:

RawStore: immutable, append-once, dated raw layer.
  write(source, name, data, dt)  -> Path  (no-op if already exists)
  read(source, name, dt)         -> bytes
  exists(source, name, dt)       -> bool
  path(source, name, dt)         -> Path  (the canonical on-disk path)

HTTPClient: a thin httpx wrapper with:
  - rate limiting (min seconds between requests to the same host)
  - exponential backoff via tenacity (429/5xx with jitter)
  - User-Agent identifying us as research scraping (good practice)
  - response stored to RawStore BEFORE parsing, so raw payloads are always
    available for debugging and re-parse without re-fetching

Leakage note: `knowable_at` for fetched data = the fetch timestamp, stored as
`{name}.meta.json` alongside the raw payload. The feature store reads this meta
to set the PIT timestamp. This is conservative (data was knowable when fetched)
and correct for any source that may retroactively correct values.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..time_utils import to_iso, utc_now

# The single User-Agent string we use everywhere.
_UA = (
    "wc2026-research/0.0.1 (academic sports prediction research; "
    "contact: samriddhi160997@gmail.com)"
)


class RawStore:
    """Immutable, append-once, dated raw payload store.

    Layout: `{root}/{source}/{YYYY-MM-DD}/{name}`
    Meta:   `{root}/{source}/{YYYY-MM-DD}/{name}.meta.json`
      -> {"fetched_utc": "...", "url": "...", "source": "...", "name": "..."}

    Re-writing an existing file is a hard error by default (idempotent pipelines
    should check .exists() first). Pass overwrite=True only for explicit refreshes.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _dir(self, source: str, dt: datetime | None = None) -> Path:
        d = dt or utc_now()
        return self.root / source / d.strftime("%Y-%m-%d")

    def path(self, source: str, name: str, dt: datetime | None = None) -> Path:
        return self._dir(source, dt) / name

    def exists(self, source: str, name: str, dt: datetime | None = None) -> bool:
        return self.path(source, name, dt).exists()

    def write(
        self,
        source: str,
        name: str,
        data: bytes | str,
        *,
        dt: datetime | None = None,
        url: str = "",
        overwrite: bool = False,
    ) -> Path:
        p = self.path(source, name, dt)
        if p.exists() and not overwrite:
            return p
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            p.write_text(data, encoding="utf-8")
        else:
            p.write_bytes(data)
        meta = {
            "fetched_utc": to_iso(utc_now()),
            "url": url,
            "source": source,
            "name": name,
        }
        p.with_suffix(p.suffix + ".meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return p

    def read(self, source: str, name: str, dt: datetime | None = None) -> bytes:
        return self.path(source, name, dt).read_bytes()

    def read_text(self, source: str, name: str, dt: datetime | None = None) -> str:
        return self.path(source, name, dt).read_text(encoding="utf-8")

    def meta(self, source: str, name: str, dt: datetime | None = None) -> dict[str, Any]:
        p = self.path(source, name, dt).with_suffix(
            self.path(source, name, dt).suffix + ".meta.json"
        )
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def fetched_at(self, source: str, name: str, dt: datetime | None = None) -> datetime | None:
        """Return the UTC fetch timestamp for a raw file, or None if not found."""
        m = self.meta(source, name, dt)
        if "fetched_utc" not in m:
            return None
        return datetime.fromisoformat(m["fetched_utc"])

    def list_dates(self, source: str) -> list[str]:
        """All date-partition dirs for a source, sorted ascending."""
        src_dir = self.root / source
        if not src_dir.exists():
            return []
        return sorted(p.name for p in src_dir.iterdir() if p.is_dir())

    def latest_date(self, source: str) -> str | None:
        dates = self.list_dates(source)
        return dates[-1] if dates else None


class HTTPClient:
    """Polite HTTP client: rate-limited per host, retries on 429/5xx, stores raw.

    Rate limiting is "at least N seconds between requests to the same host"
    implemented as wall-clock tracking, not a queue, so it is safe for single-
    threaded sequential use (which is all we need - see ADR-0002 on not
    over-engineering).
    """

    def __init__(
        self,
        store: RawStore,
        *,
        min_request_interval: float = 2.0,  # seconds between requests to the same host
        timeout: float = 30.0,
    ) -> None:
        self._store = store
        self._min_interval = min_request_interval
        self._last_request: dict[str, float] = defaultdict(float)
        self._client = httpx.Client(
            headers={"User-Agent": _UA},
            timeout=timeout,
            follow_redirects=True,
        )

    def _throttle(self, url: str) -> None:
        host = httpx.URL(url).host
        elapsed = time.monotonic() - self._last_request[host]
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request[host] = time.monotonic()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _get_raw(self, url: str, **kwargs: Any) -> httpx.Response:
        self._throttle(url)
        r = self._client.get(url, **kwargs)
        if r.status_code in (429, 500, 502, 503, 504):
            r.raise_for_status()
        return r

    def fetch(
        self,
        url: str,
        source: str,
        name: str,
        *,
        dt: datetime | None = None,
        overwrite: bool = False,
        params: dict[str, Any] | None = None,
    ) -> Path:
        """Fetch url, store raw to RawStore, return the path.

        If the file already exists and overwrite=False, returns immediately
        without hitting the network. This makes pipelines idempotent.
        """
        if not overwrite and self._store.exists(source, name, dt):
            return self._store.path(source, name, dt)
        r = self._get_raw(url, params=params)
        r.raise_for_status()
        return self._store.write(source, name, r.content, dt=dt, url=url, overwrite=overwrite)

    def fetch_json(
        self,
        url: str,
        source: str,
        name: str,
        *,
        dt: datetime | None = None,
        overwrite: bool = False,
        params: dict[str, Any] | None = None,
    ) -> tuple[Path, Any]:
        """Fetch, store, and also return parsed JSON (avoids a double read)."""
        p = self.fetch(url, source, name, dt=dt, overwrite=overwrite, params=params)
        return p, json.loads(self._store.read(source, name, dt))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def today_utc() -> datetime:
    """Current UTC date at midnight (for date-partitioned raw store keys)."""
    now = utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
