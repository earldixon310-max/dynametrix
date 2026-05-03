"""Smoke tests for password hashing + tokens."""
import os
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")

import jwt
import pytest

from app.core.security import (
    create_token, decode_token, hash_password, verify_password,
)


def test_password_round_trip():
    h = hash_password("CorrectHorse-123")
    assert verify_password("CorrectHorse-123", h)
    assert not verify_password("wrong", h)


def test_password_min_length():
    with pytest.raises(ValueError):
        hash_password("short")


def test_token_round_trip():
    tok = create_token("user-1", "access", extra_claims={"role": "admin"})
    payload = decode_token(tok, expected_type="access")
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_token_type_mismatch():
    tok = create_token("user-1", "refresh")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tok, expected_type="access")
