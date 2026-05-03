"""Audit log read endpoint (admins only)."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_admin
from app.db.models import AuditLog
from app.db.session import get_db
from app.deps import AuthenticatedUser
from app.schemas.admin import AuditOut

router = APIRouter()


@router.get("", response_model=List[AuditOut])
def list_audit(
    location_id: Optional[UUID] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    q = select(AuditLog).where(AuditLog.customer_id == current_user.customer_id)
    if location_id:
        q = q.where(AuditLog.location_id == location_id)
    if action:
        q = q.where(AuditLog.action == action)
    q = q.order_by(AuditLog.at.desc()).limit(limit)
    rows = list(db.scalars(q))
    return [
        AuditOut(
            id=r.id, at=r.at, action=r.action.value,
            user_id=r.user_id, customer_id=r.customer_id, location_id=r.location_id,
            model_version=r.model_version, ip_address=r.ip_address, context=r.context,
        )
        for r in rows
    ]
