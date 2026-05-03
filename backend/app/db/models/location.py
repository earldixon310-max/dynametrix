"""Locations a customer wants monitored."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, Float, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Location(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_customer_id", "customer_id"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(512))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(64))  # IANA tz, e.g. America/New_York
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    customer = relationship("Customer", back_populates="locations")
