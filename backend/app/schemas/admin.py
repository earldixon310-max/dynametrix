"""Admin/customer management shapes."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class CustomerOut(ORMModel):
    id: UUID
    company_name: str
    contact_name: str
    contact_email: EmailStr
    is_active: bool
    onboarding_completed_at: Optional[datetime]
    created_at: datetime


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, max_length=255)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superadmin: bool
    mfa_enabled: bool
    last_login_at: Optional[datetime]
    role: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(pattern=r"^(admin|analyst|viewer)$")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(default=None, pattern=r"^(admin|analyst|viewer)$")


class AuditOut(ORMModel):
    id: UUID
    at: datetime
    action: str
    user_id: Optional[UUID]
    customer_id: Optional[UUID]
    location_id: Optional[UUID]
    model_version: Optional[str]

    model_config = {
        "protected_namespaces": ()
    }
    ip_address: Optional[str]
    context: Optional[dict]
