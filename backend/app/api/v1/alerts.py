"""Alert history + per-customer alert settings."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_analyst, require_viewer
from app.db.models import Alert, AlertSetting
from app.db.session import get_db
from app.deps import AuthenticatedUser
from app.schemas.alerts import AlertOut, AlertSettingOut, AlertSettingUpdate

router = APIRouter()


@router.get("", response_model=List[AlertOut])
def list_alerts(
    location_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_viewer()),
):
    q = select(Alert).where(Alert.customer_id == current_user.customer_id)
    if location_id:
        q = q.where(Alert.location_id == location_id)
    q = q.order_by(Alert.triggered_at.desc()).limit(limit)
    rows = list(db.scalars(q))
    return [
        AlertOut(
            id=r.id, location_id=r.location_id, triggered_at=r.triggered_at,
            event_type=r.event_type.value, confidence=r.confidence,
            channel=r.channel.value, delivery_status=r.delivery_status.value,
            delivered_at=r.delivered_at, delivery_response=r.delivery_response,
        )
        for r in rows
    ]


@router.get("/settings", response_model=List[AlertSettingOut])
def list_settings(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_viewer()),
):
    rows = list(db.scalars(
        select(AlertSetting).where(AlertSetting.customer_id == current_user.customer_id)
    ))
    return rows


@router.patch("/settings/{setting_id}", response_model=AlertSettingOut)
def update_setting(
    setting_id: UUID,
    payload: AlertSettingUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_analyst()),
):
    s = db.get(AlertSetting, setting_id)
    if not s or s.customer_id != current_user.customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert setting not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "email_recipients" in update_data and update_data["email_recipients"] is not None:
        update_data["email_recipients"] = [str(e) for e in update_data["email_recipients"]]

    for k, v in update_data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s
