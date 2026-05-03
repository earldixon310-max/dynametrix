"""Billing schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.db.models.subscription import PlanCode
from app.schemas.common import ORMModel


class CheckoutRequest(BaseModel):
    plan: PlanCode


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionOut(ORMModel):
    id: UUID
    plan_code: PlanCode
    status: str
    stripe_subscription_id: Optional[str]
    current_period_end: Optional[datetime]
    canceled_at: Optional[datetime]

    @classmethod
    def from_orm_with_status(cls, obj):
        # SubscriptionStatus enum -> string
        d = {**obj.__dict__}
        if hasattr(d.get("status"), "value"):
            d["status"] = d["status"].value
        return cls(**d)
