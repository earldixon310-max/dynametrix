"""Alerts: per-customer settings + delivered alert records."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Float, ForeignKey, DateTime, Boolean, Enum as SAEnum,
    Integer, JSON, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.engine import EventType


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"   # within cooldown / below threshold


class AlertSetting(Base, UUIDMixin, TimestampMixin):
    """Per-customer (or per-location) alerting configuration."""
    __tablename__ = "alert_settings"
    __table_args__ = (
        Index("ix_alert_settings_customer_id", "customer_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    # Optional: scope to a single location. NULL = customer-wide default.
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE")
    )

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_recipients: Mapped[Optional[list]] = mapped_column(JSON)  # list[str]

    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(512))
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255))

    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.65, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Which event types trigger alerts (subset of EventType enum names)
    enabled_event_types: Mapped[Optional[list]] = mapped_column(JSON)


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_customer_id", "customer_id"),
        Index("ix_alerts_location_id", "location_id"),
        Index("ix_alerts_triggered_at", "triggered_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    calibrated_output_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibrated_outputs.id", ondelete="SET NULL")
    )

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="event_type", create_type=False), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    channel: Mapped[AlertChannel] = mapped_column(SAEnum(AlertChannel, name="alert_channel"), nullable=False)
    delivery_status: Mapped[AlertDeliveryStatus] = mapped_column(
        SAEnum(AlertDeliveryStatus, name="alert_delivery_status"),
        nullable=False, default=AlertDeliveryStatus.PENDING,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivery_response: Mapped[Optional[str]] = mapped_column(String(2048))

    # Snapshot of the message text at send-time (so historical reads stay stable).
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
