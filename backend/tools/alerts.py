"""
STUB engine helper. Replace with the real `tools/alerts.py`.

The SaaS layer's `app.services.alert_service` is the canonical alert dispatcher.
This file is here for backwards compatibility with any direct callers in the
existing engine; the SaaS layer does NOT import from it directly.
"""
import json
from typing import Iterable


def send_email_alert(*, to: Iterable[str], subject: str, body: str) -> bool:
    """No-op stub; the SaaS app uses smtplib through alert_service."""
    print(f"[stub] email -> {list(to)}: {subject}")
    return True


def send_webhook_alert(*, url: str, payload: dict) -> bool:
    """No-op stub; the SaaS app uses httpx through alert_service."""
    print(f"[stub] webhook -> {url}: {json.dumps(payload)[:200]}")
    return True
