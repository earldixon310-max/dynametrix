"""
Stripe billing endpoints:
- POST /billing/checkout      → returns hosted checkout URL
- POST /billing/portal        → returns hosted billing portal URL
- POST /billing/webhook       → Stripe -> us; updates Subscription.status
- GET  /billing/subscription  → current subscription state for the caller's customer
"""
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.rbac import require_admin
from app.db.models import AuditAction, Customer, Subscription, SubscriptionStatus, PlanCode
from app.db.session import get_db
from app.deps import AuthenticatedUser, get_current_user
from app.schemas.billing import (
    CheckoutRequest, CheckoutResponse, PortalResponse, SubscriptionOut,
)
from app.services import audit
from app.services.stripe_service import (
    PLAN_TO_PRICE, STRIPE_STATUS_MAP, create_billing_portal_session,
    create_checkout_session, ensure_stripe_customer, verify_webhook,
)

router = APIRouter()
log = get_logger(__name__)


def _customer_for_user(db: Session, current_user: AuthenticatedUser) -> Customer:
    if not current_user.customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User has no customer; complete onboarding first.")
    cust = db.get(Customer, current_user.customer_id)
    if not cust:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return cust


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    cust = _customer_for_user(db, current_user)
    if not PLAN_TO_PRICE.get(payload.plan):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Plan {payload.plan} is not available.")

    cust.stripe_customer_id = ensure_stripe_customer(
        email=cust.contact_email, name=cust.company_name, existing_id=cust.stripe_customer_id,
    )
    db.add(cust)
    db.flush()
    url = create_checkout_session(customer_id=cust.stripe_customer_id, plan=payload.plan)
    db.commit()
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def portal(db: Session = Depends(get_db),
           current_user: AuthenticatedUser = Depends(require_admin())):
    cust = _customer_for_user(db, current_user)
    if not cust.stripe_customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Stripe customer on file. Run checkout first.")
    url = create_billing_portal_session(customer_id=cust.stripe_customer_id)
    return PortalResponse(portal_url=url)


@router.get("/subscription", response_model=Optional[SubscriptionOut])
def my_subscription(db: Session = Depends(get_db),
                    current_user: AuthenticatedUser = Depends(get_current_user)):
    if not current_user.customer_id:
        return None
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.customer_id == current_user.customer_id)
        .order_by(Subscription.created_at.desc())
    )
    if not sub:
        return None
    return SubscriptionOut.from_orm_with_status(sub)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    body = await request.body()
    try:
        event = verify_webhook(body, stripe_signature)
    except (stripe.error.SignatureVerificationError, ValueError, RuntimeError) as exc:
        log.warning("billing.webhook.invalid_signature", error=str(exc))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature")

    event_type = event["type"]
    obj = event["data"]["object"]
    log.info("billing.webhook.received", type=event_type)

    # We handle the canonical subscription lifecycle events.
    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }:
        stripe_customer_id = obj.get("customer") if isinstance(obj, dict) else None
        if not stripe_customer_id:
            return {"ok": True}

        customer = db.scalar(
            select(Customer).where(Customer.stripe_customer_id == stripe_customer_id)
        )
        if not customer:
            log.warning("billing.webhook.unknown_customer", id=stripe_customer_id)
            return {"ok": True}

        sub = db.scalar(
            select(Subscription)
            .where(Subscription.customer_id == customer.id)
            .order_by(Subscription.created_at.desc())
        )
        if not sub:
            return {"ok": True}

        # Pull current sub state from the event payload when we can
        if event_type.startswith("customer.subscription"):
            sub.stripe_subscription_id = obj.get("id", sub.stripe_subscription_id)
            mapped = STRIPE_STATUS_MAP.get(obj.get("status", ""), sub.status)
            old_status = sub.status
            sub.status = mapped
            cps = obj.get("current_period_start")
            cpe = obj.get("current_period_end")
            if cps: sub.current_period_start = datetime.fromtimestamp(cps, tz=timezone.utc)
            if cpe: sub.current_period_end = datetime.fromtimestamp(cpe, tz=timezone.utc)
            if event_type == "customer.subscription.deleted":
                sub.status = SubscriptionStatus.CANCELED
                sub.canceled_at = datetime.now(timezone.utc)
            if old_status != sub.status:
                audit.record(
                    db, action=AuditAction.BILLING_STATUS_CHANGED,
                    customer_id=customer.id,
                    context={"from": old_status.value if hasattr(old_status, 'value') else str(old_status),
                             "to": sub.status.value if hasattr(sub.status, 'value') else str(sub.status)},
                )

        db.commit()

    return {"ok": True}
