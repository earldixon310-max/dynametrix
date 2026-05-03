"""
Audit log writer.

Always use this helper to record auditable actions. Never bypass it. The function
is sync and writes inside the caller's transaction so the audit row commits atomically
with the action it describes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLog, AuditAction


def record(
    db: Session,
    *,
    action: AuditAction,
    customer_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    location_id: Optional[uuid.UUID] = None,
    model_version: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    context: Optional[dict] = None,
) -> AuditLog:
    """Insert an audit row. Caller commits."""
    row = AuditLog(
        at=datetime.now(timezone.utc),
        action=action,
        customer_id=customer_id,
        user_id=user_id,
        location_id=location_id,
        model_version=model_version,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:512] or None,
        context=_sanitize(context),
    )
    db.add(row)
    return row


_FORBIDDEN_KEYS = {"password", "password_hash", "token", "secret", "api_key", "authorization"}


def _sanitize(ctx: Optional[dict]) -> Optional[dict]:
    if not ctx:
        return None
    return {k: ("***REDACTED***" if k.lower() in _FORBIDDEN_KEYS else v) for k, v in ctx.items()}
