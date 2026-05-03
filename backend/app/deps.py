"""
Cross-cutting FastAPI dependencies.

- get_db: SQLAlchemy session
- get_current_user: decode JWT, load user, attach role + customer_id
- require_active_subscription: gate dashboards behind paid status
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import CustomerUser, Subscription, User
from app.db.models.subscription import ACTIVE_STATUSES
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    id: UUID
    email: str
    full_name: str
    is_superadmin: bool
    customer_id: Optional[UUID]
    role: Optional[str]
    mfa_enabled: bool


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject")

    user = db.get(User, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    link = db.scalar(select(CustomerUser).where(CustomerUser.user_id == user.id))
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_superadmin=user.is_superadmin,
        customer_id=(link.customer_id if link else None),
        role=(link.role if link else None),
        mfa_enabled=user.mfa_enabled,
    )


def require_active_subscription(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Block dashboard access when the customer has no active subscription."""
    if current_user.is_superadmin:
        return current_user
    if not current_user.customer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not associated with a customer")
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.customer_id == current_user.customer_id)
        .order_by(Subscription.created_at.desc())
    )
    if not sub or sub.status not in ACTIVE_STATUSES:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Subscription is not active. Please complete or update billing.",
        )
    return current_user
