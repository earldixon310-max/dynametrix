"""Auth request/response shapes."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=256)


class CurrentUser(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_superadmin: bool
    customer_id: Optional[UUID] = None
    role: Optional[str] = None
    mfa_enabled: bool = False
