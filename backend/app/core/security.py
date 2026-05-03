"""
Password hashing and JWT utilities.

- Argon2id for password storage (resistant to GPU attacks).
- JWTs signed with HS256 by default. Swap to RS256 for prod by setting JWT_ALGORITHM
  and providing PEM-encoded keys via env vars.
- Refresh tokens are issued with a `jti` claim so they can be revoked server-side
  on logout / rotation.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

from app.core.config import get_settings

settings = get_settings()
_hasher = PasswordHasher()  # Argon2id with library defaults


# ---------- Password ----------

def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verification of plaintext against an Argon2 hash."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(hashed: str) -> bool:
    """Return True if the hash params are out-of-date and we should rehash on next login."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHash:
        return True


# ---------- Tokens ----------

TokenType = Literal["access", "refresh", "password_reset", "mfa_challenge"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    subject: str,
    token_type: TokenType,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT.

    `subject` is normally the user_id (UUID string). `extra_claims` lets callers
    embed customer_id, role, etc. Never put secrets or PII in claims — they're
    base64-encoded, not encrypted.
    """
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MIN)
        elif token_type == "refresh":
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        elif token_type == "password_reset":
            expires_delta = timedelta(hours=1)
        else:  # mfa_challenge
            expires_delta = timedelta(minutes=5)

    now = _now()
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: Optional[TokenType] = None) -> Dict[str, Any]:
    """
    Decode and verify a JWT. Raises jwt.PyJWTError subclasses on failure.

    If `expected_type` is given, the `type` claim must match — this prevents an
    attacker from using a refresh token where an access token is required.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type {expected_type}, got {payload.get('type')}")
    return payload


def generate_password_reset_token(user_id: str, email: str) -> str:
    return create_token(user_id, "password_reset", extra_claims={"email": email})


def generate_csrf_token() -> str:
    """Cryptographically random token for CSRF double-submit cookies."""
    return secrets.token_urlsafe(32)
