"""Subscription / billing state."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PlanCode(str, enum.Enum):
    TRIAL = "trial"
    SINGLE = "single_location"
    MULTI = "multi_location"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


# Statuses that grant access to dashboard data
ACTIVE_STATUSES = {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_customer_id", "customer_id"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    plan_code: Mapped[PlanCode] = mapped_column(SAEnum(PlanCode, name="plan_code"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.INCOMPLETE,
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(64))

    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer = relationship("Customer", back_populates="subscriptions")

    @property
    def grants_access(self) -> bool:
        return self.status in ACTIVE_STATUSES
