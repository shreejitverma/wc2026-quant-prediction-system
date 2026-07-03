"""Push notifications via ntfy (Phase 6): the simplest thing that works.

Disabled by default (`notify.enabled: false` in config); nothing is sent
unless the operator opts in with a topic. Intended caller is the real alert
engine when it exists - mock alerts must never page a phone. The topic name
is effectively a capability token: it lives in config on the backend and
never reaches the frontend.
"""

from __future__ import annotations

import urllib.request

_PRIORITY = {"info": "default", "warn": "high", "critical": "urgent"}


def send_ntfy(
    url: str,
    topic: str,
    title: str,
    message: str,
    severity: str = "info",
    timeout_s: float = 5.0,
) -> bool:
    """POST one notification. Returns False on any failure - alerting must
    degrade to in-app only, never take the API down with it."""
    try:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/{topic}",
            data=message.encode(),
            headers={
                "Title": title,
                "Priority": _PRIORITY.get(severity, "default"),
                "Tags": "rotating_light" if severity == "critical" else "warning",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def format_alert(alert: dict) -> tuple[str, str]:
    """(title, body) for a pushed alert; keep it readable on a lock screen."""
    return (
        f"WC2026 {alert.get('severity', 'info').upper()}: {alert.get('kind', 'alert')}",
        str(alert.get("message", ""))[:500] + f"\n\n(id {alert.get('alert_id', '?')})",
    )
