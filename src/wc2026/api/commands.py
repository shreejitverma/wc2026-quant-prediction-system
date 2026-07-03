"""Fenced command layer (Phase 4, ADR-0011): the UI's ONLY write path.

Command state is DERIVED FROM THE LEDGER, never held in process memory:
every accepted command appends a kind="command" entry, and the current state
(killed? which tickers paused? widen factor?) is a fold over those entries.
Restart-safe, tamper-evident, one source of truth - the write path is the
audit trail. These are real ledger writes even while quoting is mock:
operator intent is real.

Fences live HERE, server-side. A UI-side disabled button is a courtesy;
these functions rejecting are the fence:
  - kill is idempotent (no duplicate entries) and has NO un-kill: re-arming
    is a deliberate CLI act, not a button;
  - resume is refused while killed and refused outside paper mode;
  - widen factor is clamped to [1.0, 3.0].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..ledger import AppendOnlyLedger
from ..time_utils import to_iso, utc_now
from .deps import ApiState

WIDEN_MIN, WIDEN_MAX = 1.0, 3.0


@dataclass
class CommandState:
    killed: bool = False
    killed_at: str | None = None
    kill_reason: str | None = None
    paused_tickers: dict[str, str] = field(default_factory=dict)  # ticker -> ts_utc
    widen_factor: float = 1.0


def fold_command_state(entries: list[dict[str, Any]]) -> CommandState:
    """Replay command entries in ledger order. The fold is the state."""
    s = CommandState()
    for e in entries:
        if e.get("kind") != "command":
            continue
        p = e.get("payload", {})
        action = p.get("action")
        if action == "kill_switch":
            s.killed = True
            s.killed_at = str(e["ts_utc"])
            s.kill_reason = p.get("reason")
        elif action == "pause_quoting" and p.get("ticker"):
            s.paused_tickers[str(p["ticker"])] = str(e["ts_utc"])
        elif action == "resume_quoting" and p.get("ticker"):
            s.paused_tickers.pop(str(p["ticker"]), None)
        elif action == "widen_all":
            s.widen_factor = float(p.get("factor", 1.0))
    return s


def read_command_state(state: ApiState) -> CommandState:
    return fold_command_state(AppendOnlyLedger(state.ledger_path).read_all())


class CommandRejected(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _append(state: ApiState, action: str, **payload: Any) -> dict[str, Any]:
    led = AppendOnlyLedger(state.ledger_path)
    return led.append(
        kind="command",
        payload={
            "action": action,
            "mode": state.cfg.mode,
            "source": "terminal-ui",
            "ts_utc": to_iso(utc_now()),
            **payload,
        },
    )


def command_kill(state: ApiState, reason: str) -> tuple[CommandState, int | None, bool]:
    """Idempotent: a second kill returns the existing state, appends nothing.
    Returns (state, ledger_seq or None, already_killed)."""
    s = read_command_state(state)
    if s.killed:
        return s, None, True
    entry = _append(state, "kill_switch", reason=reason)
    return read_command_state(state), int(entry["seq"]), False


def command_pause(state: ApiState, ticker: str, reason: str | None) -> tuple[CommandState, int | None]:
    s = read_command_state(state)
    if ticker in s.paused_tickers:  # idempotent, no duplicate entry
        return s, None
    entry = _append(state, "pause_quoting", ticker=ticker, reason=reason)
    return read_command_state(state), int(entry["seq"])


def command_resume(state: ApiState, ticker: str, reason: str | None) -> tuple[CommandState, int | None]:
    if state.cfg.mode != "paper":
        raise CommandRejected(
            "live_resume_forbidden",
            "Resume outside paper mode requires the CLI and a pre-registration gate.",
        )
    s = read_command_state(state)
    if s.killed:
        raise CommandRejected(
            "killed",
            "Kill switch is active; resume is refused. Re-arming is a deliberate CLI act.",
        )
    if ticker not in s.paused_tickers:  # idempotent
        return s, None
    entry = _append(state, "resume_quoting", ticker=ticker, reason=reason)
    return read_command_state(state), int(entry["seq"])


def command_widen(state: ApiState, factor: float) -> tuple[CommandState, int]:
    clamped = max(WIDEN_MIN, min(WIDEN_MAX, factor))
    entry = _append(state, "widen_all", factor=clamped, requested_factor=factor)
    return read_command_state(state), int(entry["seq"])
