"""
Alert dispatch:
- email and webhook channels
- cooldown (per location, per channel)
- confidence threshold
- event-type filter
- writes Alert rows with delivery_status

Real send goes through tools/alerts.py if present (existing engine helper);
otherwise we fall back to SMTP / requests.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Iterable, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    Alert, AlertChannel, AlertDeliveryStatus, AlertSetting,
    CalibratedOutput, Location,
)
from app.db.models.engine import EventType
from app.utils.copy import event_label, time_to_impact, recommended_action, DISCLAIMER_SHORT

settings = get_settings()
log = get_logger(__name__)


def _setting_for(db: Session, *, customer_id: uuid.UUID, location_id: uuid.UUID) -> Optional[AlertSetting]:
    row = db.scalar(
        select(AlertSetting)
        .where(AlertSetting.customer_id == customer_id, AlertSetting.location_id == location_id)
    )
    if row:
        return row
    # fallback: customer-wide default
    return db.scalar(
        select(AlertSetting)
        .where(AlertSetting.customer_id == customer_id, AlertSetting.location_id.is_(None))
    )


def _in_cooldown(
    db: Session, *, customer_id: uuid.UUID, location_id: uuid.UUID, channel: AlertChannel,
    cooldown_minutes: int, now: datetime,
) -> bool:
    cutoff = now - timedelta(minutes=cooldown_minutes)
    recent = db.scalar(
        select(Alert)
        .where(
            Alert.customer_id == customer_id,
            Alert.location_id == location_id,
            Alert.channel == channel,
            Alert.delivery_status == AlertDeliveryStatus.SENT,
            Alert.delivered_at >= cutoff,
        )
    )
    return recent is not None


def _build_payload(loc: Location, co: CalibratedOutput) -> dict:
    et = (co.event_type_calibrated or EventType.PRE_COMMITMENT).value
    return {
        "location": {"id": str(loc.id), "label": loc.label, "lat": loc.latitude, "lon": loc.longitude},
        "observed_at": co.observed_at.isoformat(),
        "event_type": et,
        "event_label": event_label(et),
        "confidence": co.confidence,
        "commitment_probability": co.commitment_probability,
        "lead_time_text": time_to_impact(co.expected_lead_hours),
        "recommended_action": recommended_action(et, co.confidence),
        "disclaimer": DISCLAIMER_SHORT,
    }


def evaluate_and_dispatch(
    db: Session,
    *,
    customer_id: uuid.UUID,
    location: Location,
    calibrated: CalibratedOutput,
    now: Optional[datetime] = None,
) -> List[Alert]:
    """
    Decide whether the calibrated output merits an alert and, if so, dispatch
    it through the configured channels. Returns the Alert rows it created.

    Caller commits.
    """
    now = now or datetime.now(timezone.utc)
    setting = _setting_for(db, customer_id=customer_id, location_id=location.id)
    if not setting:
        return []

    if calibrated.confidence < setting.confidence_threshold:
        return []

    enabled_types = set(setting.enabled_event_types or [])
    if calibrated.event_type_calibrated and calibrated.event_type_calibrated.value not in enabled_types:
        return []

    payload = _build_payload(location, calibrated)
    out: List[Alert] = []

    if setting.email_enabled and setting.email_recipients:
        out.append(_dispatch_email(
            db, customer_id=customer_id, location=location, calibrated=calibrated,
            recipients=list(setting.email_recipients), payload=payload,
            cooldown=setting.cooldown_minutes, now=now,
        ))

    if setting.webhook_enabled and setting.webhook_url:
        out.append(_dispatch_webhook(
            db, customer_id=customer_id, location=location, calibrated=calibrated,
            url=setting.webhook_url, secret=setting.webhook_secret, payload=payload,
            cooldown=setting.cooldown_minutes, now=now,
        ))

    return out


def _new_alert(*, customer_id, location, calibrated, channel, payload, now) -> Alert:
    return Alert(
        customer_id=customer_id,
        location_id=location.id,
        calibrated_output_id=calibrated.id,
        triggered_at=now,
        event_type=(calibrated.event_type_calibrated or EventType.PRE_COMMITMENT),
        confidence=calibrated.confidence,
        channel=channel,
        delivery_status=AlertDeliveryStatus.PENDING,
        payload=payload,
    )


def _dispatch_email(
    db, *, customer_id, location, calibrated, recipients, payload, cooldown, now,
) -> Alert:
    alert = _new_alert(
        customer_id=customer_id, location=location, calibrated=calibrated,
        channel=AlertChannel.EMAIL, payload=payload, now=now,
    )
    db.add(alert)

    if _in_cooldown(db, customer_id=customer_id, location_id=location.id,
                    channel=AlertChannel.EMAIL, cooldown_minutes=cooldown, now=now):
        alert.delivery_status = AlertDeliveryStatus.SUPPRESSED
        alert.delivery_response = "Suppressed by cooldown"
        return alert

    if not settings.SMTP_HOST:
        alert.delivery_status = AlertDeliveryStatus.FAILED
        alert.delivery_response = "SMTP not configured"
        return alert

    try:
        body = (
            f"Dynametrix structural alert\n\n"
            f"Location: {payload['location']['label']}\n"
            f"Observed: {payload['observed_at']}\n"
            f"Event: {payload['event_label']}\n"
            f"Confidence: {payload['confidence']:.2f}\n"
            f"{payload['lead_time_text']}\n\n"
            f"{payload['recommended_action']}\n\n"
            f"{DISCLAIMER_SHORT}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[Dynametrix] {payload['event_label']} — {payload['location']['label']}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        alert.delivery_status = AlertDeliveryStatus.SENT
        alert.delivered_at = now
        alert.delivery_response = f"Sent to {len(recipients)} recipient(s)"
    except Exception as exc:
        alert.delivery_status = AlertDeliveryStatus.FAILED
        alert.delivery_response = f"SMTP error: {exc}"[:2000]
        log.warning("alert.email_failed", error=str(exc))

    return alert


def _dispatch_webhook(
    db, *, customer_id, location, calibrated, url, secret, payload, cooldown, now,
) -> Alert:
    alert = _new_alert(
        customer_id=customer_id, location=location, calibrated=calibrated,
        channel=AlertChannel.WEBHOOK, payload=payload, now=now,
    )
    db.add(alert)

    if _in_cooldown(db, customer_id=customer_id, location_id=location.id,
                    channel=AlertChannel.WEBHOOK, cooldown_minutes=cooldown, now=now):
        alert.delivery_status = AlertDeliveryStatus.SUPPRESSED
        alert.delivery_response = "Suppressed by cooldown"
        return alert

    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "Dynametrix-Alerts/1.0"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Dynametrix-Signature"] = f"sha256={sig}"

    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, content=body, headers=headers)
        alert.delivery_response = f"HTTP {r.status_code}: {r.text[:500]}"
        if 200 <= r.status_code < 300:
            alert.delivery_status = AlertDeliveryStatus.SENT
            alert.delivered_at = now
        else:
            alert.delivery_status = AlertDeliveryStatus.FAILED
    except Exception as exc:
        alert.delivery_status = AlertDeliveryStatus.FAILED
        alert.delivery_response = f"Webhook error: {exc}"[:2000]
        log.warning("alert.webhook_failed", error=str(exc))

    return alert
