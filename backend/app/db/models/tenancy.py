"""
Multi-tenant identity tables: customers, users, customer_users.

A `User` belongs to exactly one `Customer` for the MVP (we record the binding
in `customer_users` to keep the schema future-proof for cross-customer access).
Tenant isolation in queries is enforced by always filtering on `customer_id`,
sourced from the JWT-derived current user — never from request body params.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    billing_address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    billing_address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    billing_city: Mapped[Optional[str]] = mapped_column(String(128))
    billing_region: Mapped[Optional[str]] = mapped_column(String(128))
    billing_postal_code: Mapped[Optional[str]] = mapped_column(String(32))
    billing_country: Mapped[Optional[str]] = mapped_column(String(2))  # ISO-3166-1 alpha-2

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ---- relationships ----
    locations: Mapped[List["Location"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    customer_users: Mapped[List["CustomerUser"]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # MFA-ready (not enforced in MVP)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted: Mapped[Optional[str]] = mapped_column(String(255))

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ---- relationships ----
    customer_users: Mapped[List["CustomerUser"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def primary_customer_id(self) -> Optional[uuid.UUID]:
        if self.customer_users:
            return self.customer_users[0].customer_id
        return None

    @property
    def primary_role(self) -> Optional[str]:
        if self.customer_users:
            return self.customer_users[0].role
        return None


class CustomerUser(Base, UUIDMixin, TimestampMixin):
    """Join table: which user belongs to which customer with what role."""
    __tablename__ = "customer_users"
    __table_args__ = (
        UniqueConstraint("customer_id", "user_id", name="uq_customer_user"),
        Index("ix_customer_users_customer_id", "customer_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # admin | analyst | viewer

    customer: Mapped["Customer"] = relationship(back_populates="customer_users")
    user: Mapped["User"] = relationship(back_populates="customer_users")
