"""Onboarding request shapes."""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.models.subscription import PlanCode


class LocationInput(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    address: Optional[str] = Field(default=None, max_length=512)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: Optional[str] = Field(default=None, max_length=64)


class AlertPrefs(BaseModel):
    email_enabled: bool = True
    email_recipients: List[EmailStr] = Field(default_factory=list)
    webhook_enabled: bool = False
    webhook_url: Optional[str] = Field(default=None, max_length=512)
    webhook_secret: Optional[str] = Field(default=None, max_length=255)
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    cooldown_minutes: int = Field(default=30, ge=0, le=24 * 60)
    enabled_event_types: List[str] = Field(
        default_factory=lambda: ["pre_commitment", "commitment", "reconfiguration"]
    )

    @field_validator("enabled_event_types")
    @classmethod
    def _check_event_types(cls, v: List[str]) -> List[str]:
        allowed = {"pre_commitment", "commitment", "reconfiguration", "false_start", "decay"}
        bad = [t for t in v if t not in allowed]
        if bad:
            raise ValueError(f"Unknown event types: {bad}")
        return v


class OnboardingPayload(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    billing_address_line1: Optional[str] = Field(default=None, max_length=255)
    billing_address_line2: Optional[str] = Field(default=None, max_length=255)
    billing_city: Optional[str] = Field(default=None, max_length=128)
    billing_region: Optional[str] = Field(default=None, max_length=128)
    billing_postal_code: Optional[str] = Field(default=None, max_length=32)
    billing_country: Optional[str] = Field(default=None, min_length=2, max_length=2)

    locations: List[LocationInput] = Field(min_length=1)
    alert_preferences: AlertPrefs = Field(default_factory=AlertPrefs)
    plan: PlanCode = PlanCode.TRIAL
    terms_accepted: bool

    @field_validator("terms_accepted")
    @classmethod
    def _must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Terms must be accepted to complete onboarding")
        return v
