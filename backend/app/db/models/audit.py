"""Append-only audit log."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class AuditAction(str, enum.Enum):
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILED = "login.failed"
    LOGOUT = "logout"
    PASSWORD_RESET_REQUESTED = "password.reset_requested"
    PASSWORD_RESET_COMPLETED = "password.reset_completed"
    DATA_REFRESH = "data.refresh"
    PIPELINE_RUN = "pipeline.run"
    ALERT_SENT = "alert.sent"
    REPORT_DOWNLOADED = "report.downloaded"
    REPORT_GENERATED = "report.generated"
    ADMIN_USER_CREATED = "admin.user_created"
    ADMIN_USER_UPDATED = "admin.user_updated"
    ADMIN_USER_DELETED = "admin.user_deleted"
    ADMIN_CUSTOMER_UPDATED = "admin.customer_updated"
    BILLING_STATUS_CHANGED = "billing.status_changed"
    SUBSCRIPTION_UPDATED = "billing.subscription_updated"


class AuditLog(Base, UUIDMixin):
    """
    Append-only. NEVER mutate or delete rows from this table from app code.
    A retention/archival job at the DB or ETL layer can rotate to cold storage.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_customer_id", "customer_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_at", "at"),
        Index("ix_audit_logs_action", "action"),
    )

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, name="audit_action"), nullable=False)

    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL")
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL")
    )

    # Free-form context: e.g. {"ip": "...", "user_agent": "...", "model_version": "..."}
    # Caller is responsible for not putting secrets/PII here.
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    model_version: Mapped[Optional[str]] = mapped_column(String(64))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
