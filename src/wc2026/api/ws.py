"""Multiplexed WebSocket: one connection, topic subscribe/unsubscribe (ADR-0014).

One socket means one reconnect path, one heartbeat, one place to resume from -
per-ticker sockets multiply exactly the code that is hardest to get right.

Protocol:
  client -> {"subscribe": ["health", "ledger", "book.<ticker>"], "after_seq": N?}
  client -> {"unsubscribe": ["book.<ticker>"]}
  server -> {"topic": str, "source": "real"|"mock", "ts_utc": iso, "data": ...}

Topics:
  health         REAL   same Envelope as GET /api/v1/health; on subscribe + every 5s
  ledger         REAL   new ledger entries past a cursor; on subscribe + 2s poll.
                        Default cursor = current head (tail only new); pass
                        "after_seq" with the subscribe to backfill from a point.
  book.<ticker>  MOCK   random-walk book; on subscribe + every 1s (until the
                        ingestion layer persists real snapshots)

Every message carries source, so a consumer of the stream is under the same
honesty contract as a consumer of the REST API.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..ledger import AppendOnlyLedger
from ..time_utils import to_iso, utc_now
from .deps import ApiState

TICK_SECONDS = 1.0
HEALTH_EVERY_TICKS = 5
LEDGER_EVERY_TICKS = 2


def _msg(topic: str, source: str, data: Any) -> dict[str, Any]:
    return {"topic": topic, "source": source, "ts_utc": to_iso(utc_now()), "data": data}


def _mock_book(ticker: str, step: int) -> dict[str, Any]:
    """Deterministic per (ticker, step): reconnecting clients see the same walk."""
    rng = random.Random(f"{ticker}:{step}")
    mid = 0.50 + 0.15 * rng.uniform(-1, 1)
    bids = [
        {"price": round(mid - 0.01 * (i + 1), 2), "size": rng.randint(100, 5000)} for i in range(5)
    ]
    asks = [
        {"price": round(mid + 0.01 * (i + 1), 2), "size": rng.randint(100, 5000)} for i in range(5)
    ]
    return {"ticker": ticker, "bids": bids, "asks": asks}


class _Conn:
    """Per-connection subscription state."""

    def __init__(self, state: ApiState) -> None:
        self.state = state
        self.subs: set[str] = set()
        self.ledger_cursor: int | None = None  # None until ledger subscribed

    def _ledger_entries_after(self, seq: int) -> list[dict[str, Any]]:
        entries = AppendOnlyLedger(self.state.ledger_path).read_all()
        return [e for e in entries if int(e["seq"]) > seq]

    def subscribe(self, topics: list[str], after_seq: int | None) -> list[dict[str, Any]]:
        """Apply a subscribe and return the immediate snapshot messages."""
        out: list[dict[str, Any]] = []
        for t in topics:
            self.subs.add(t)
            if t == "health":
                out.append(self.health_message())
            elif t == "ledger":
                if after_seq is not None:
                    self.ledger_cursor = after_seq
                else:
                    # Tail-only by default: start at the current head.
                    entries = AppendOnlyLedger(self.state.ledger_path).read_all()
                    self.ledger_cursor = int(entries[-1]["seq"]) if entries else -1
                out.extend(self.ledger_messages())
            elif t.startswith("book."):
                out.append(_msg(t, "mock", _mock_book(t.removeprefix("book."), step=0)))
        return out

    def health_message(self) -> dict[str, Any]:
        from .server import build_health_envelope  # local import: avoids a cycle

        env = build_health_envelope(self.state)
        return _msg("health", "real", env.model_dump(mode="json"))

    def ledger_messages(self) -> list[dict[str, Any]]:
        if self.ledger_cursor is None:
            return []
        fresh = self._ledger_entries_after(self.ledger_cursor)
        if not fresh:
            return []
        self.ledger_cursor = int(fresh[-1]["seq"])
        return [_msg("ledger", "real", {"entries": fresh})]

    def tick_messages(self, step: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for t in sorted(self.subs):
            if t.startswith("book."):
                out.append(_msg(t, "mock", _mock_book(t.removeprefix("book."), step=step)))
        if "health" in self.subs and step % HEALTH_EVERY_TICKS == 0:
            out.append(self.health_message())
        if "ledger" in self.subs and step % LEDGER_EVERY_TICKS == 0:
            out.extend(self.ledger_messages())
        return out


async def serve_ws(websocket: WebSocket, state: ApiState) -> None:
    await websocket.accept()
    conn = _Conn(state)
    send_lock = asyncio.Lock()

    async def send_all(messages: list[dict[str, Any]]) -> None:
        async with send_lock:
            for m in messages:
                await websocket.send_json(m)

    async def reader() -> None:
        while True:
            req = await websocket.receive_json()
            if subs := req.get("subscribe"):
                await send_all(conn.subscribe(list(subs), req.get("after_seq")))
            if unsubs := req.get("unsubscribe"):
                conn.subs.difference_update(unsubs)

    reader_task = asyncio.create_task(reader())
    step = 0
    try:
        while True:
            if reader_task.done():
                reader_task.result()  # surface WebSocketDisconnect / errors
                return
            await asyncio.sleep(TICK_SECONDS)
            step += 1
            await send_all(conn.tick_messages(step))
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, Exception):
            await reader_task
