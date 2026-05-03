"""
Authentication endpoints: login, refresh, logout, password reset, /me.

CSRF: tokens are issued in JSON, not cookies, so the API surface is not
vulnerable to classic CSRF. The Next.js frontend stores access tokens in
memory (or HttpOnly cookies set by a Next API route) — see frontend/lib/auth.ts.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_token, decode_token, hash_password, needs_rehash, verify_password,
    generate_password_reset_token,
)
from app.db.models import AuditAction, CustomerUser, User
from app.db.session import get_db
from app.deps import AuthenticatedUser, get_current_user
from app.schemas.auth import (
    CurrentUser, LoginRequest, PasswordResetConfirm, PasswordResetRequest,
    RefreshRequest, TokenPair,
)
from app.schemas.common import Message
from app.services import audit

router = APIRouter()

# Lockout policy
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


def _claims_for(user: User, link: Optional[CustomerUser]) -> dict:
    return {
        "email": user.email,
        "role": link.role if link else None,
        "customer_id": str(link.customer_id) if link else None,
    }


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not user or not user.is_active:
        audit.record(db, action=AuditAction.LOGIN_FAILED,
                     context={"reason": "no_user_or_inactive", "email": payload.email},
                     ip_address=ip, user_agent=ua)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_423_LOCKED, "Account temporarily locked. Try again later.")

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = datetime.now(timezone.utc).replace(microsecond=0) \
                + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        audit.record(db, action=AuditAction.LOGIN_FAILED, user_id=user.id,
                     context={"reason": "bad_password"}, ip_address=ip, user_agent=ua)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    # Successful login
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)

    link = db.scalar(select(CustomerUser).where(CustomerUser.user_id == user.id))
    extra = _claims_for(user, link)
    access = create_token(str(user.id), "access", extra_claims=extra)
    refresh = create_token(str(user.id), "refresh", extra_claims=extra)

    audit.record(db, action=AuditAction.LOGIN_SUCCESS, user_id=user.id,
                 customer_id=(link.customer_id if link else None),
                 ip_address=ip, user_agent=ua)
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.get(User, UUID(claims["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    link = db.scalar(select(CustomerUser).where(CustomerUser.user_id == user.id))
    extra = _claims_for(user, link)
    return TokenPair(
        access_token=create_token(str(user.id), "access", extra_claims=extra),
        refresh_token=create_token(str(user.id), "refresh", extra_claims=extra),
    )


@router.post("/logout", response_model=Message)
def logout(current_user: AuthenticatedUser = Depends(get_current_user),
           db: Session = Depends(get_db), request: Request = None):
    # Stateless JWT: client must drop the token. We log the event for audit purposes.
    audit.record(db, action=AuditAction.LOGOUT, user_id=current_user.id,
                 customer_id=current_user.customer_id,
                 ip_address=(request.client.host if request and request.client else None),
                 user_agent=(request.headers.get("user-agent") if request else None))
    db.commit()
    return Message(detail="Logged out")


@router.post("/password/reset/request", response_model=Message)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    # Always respond with the same message — never disclose whether the email exists.
    if user:
        token = generate_password_reset_token(str(user.id), user.email)
        # In production, hand `token` to email service. For now we log it (dev only).
        audit.record(db, action=AuditAction.PASSWORD_RESET_REQUESTED, user_id=user.id,
                     context={"reset_link_token_first8": token[:8]})
        db.commit()
    return Message(detail="If that email exists, a reset link has been sent.")


@router.post("/password/reset/confirm", response_model=Message)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.token, expected_type="password_reset")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
    user = db.get(User, UUID(claims["sub"]))
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token")
    user.password_hash = hash_password(payload.new_password)
    audit.record(db, action=AuditAction.PASSWORD_RESET_COMPLETED, user_id=user.id)
    db.commit()
    return Message(detail="Password updated")


@router.get("/me", response_model=CurrentUser)
def me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return CurrentUser(
        id=current_user.id, email=current_user.email, full_name=current_user.full_name,
        is_superadmin=current_user.is_superadmin, customer_id=current_user.customer_id,
        role=current_user.role, mfa_enabled=current_user.mfa_enabled,
    )
