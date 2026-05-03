"""Alert schemas."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from app.schemas.common import ORMModel


class AlertOut(ORMModel):
    id: UUID
    location_id: UUID
    triggered_at: datetime
    event_type: str
    confidence: float
    channel: str
    delivery_status: str
    delivered_at: Optional[datetime]
    delivery_response: Optional[str]


class AlertSettingOut(ORMModel):
    id: UUID
    location_id: Optional[UUID]
    email_enabled: bool
    email_recipients: Optional[List[EmailStr]]
    webhook_enabled: bool
    webhook_url: Optional[str]
    confidence_threshold: float
    cooldown_minutes: int
    enabled_event_types: Optional[List[str]]


class AlertSettingUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    email_recipients: Optional[List[EmailStr]] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = Field(default=None, max_length=512)
    webhook_secret: Optional[str] = Field(default=None, max_length=255)
    confidence_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    cooldown_minutes: Optional[int] = Field(default=None, ge=0, le=24 * 60)
    enabled_event_types: Optional[List[str]] = None
