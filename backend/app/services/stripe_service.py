"""
Stripe integration: customers, checkout sessions, billing portal, webhooks.

Map of plans -> Stripe price IDs is loaded from settings (env vars).
"""
from __future__ import annotations

from typing import Optional

import stripe

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.subscription import PlanCode, SubscriptionStatus

settings = get_settings()
log = get_logger(__name__)

if settings.STRIPE_API_KEY:
    stripe.api_key = settings.STRIPE_API_KEY


PLAN_TO_PRICE = {
    PlanCode.TRIAL: settings.STRIPE_PRICE_TRIAL,
    PlanCode.SINGLE: settings.STRIPE_PRICE_SINGLE,
    PlanCode.MULTI: settings.STRIPE_PRICE_MULTI,
    PlanCode.ENTERPRISE: settings.STRIPE_PRICE_ENTERPRISE,
}


# Stripe -> internal status
STRIPE_STATUS_MAP = {
    "incomplete": SubscriptionStatus.INCOMPLETE,
    "incomplete_expired": SubscriptionStatus.CANCELED,
    "trialing": SubscriptionStatus.TRIALING,
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "unpaid": SubscriptionStatus.UNPAID,
}


def ensure_stripe_customer(*, email: str, name: str, existing_id: Optional[str]) -> str:
    """Return a Stripe customer id, creating one if needed."""
    if existing_id:
        return existing_id
    cust = stripe.Customer.create(email=email, name=name, metadata={"source": "dynametrix"})
    return cust["id"]


def create_checkout_session(*, customer_id: str, plan: PlanCode) -> str:
    """Returns the Checkout URL the user should be redirected to."""
    price_id = PLAN_TO_PRICE.get(plan)
    if not price_id:
        raise ValueError(f"No price ID configured for plan {plan}")
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
        cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
        allow_promotion_codes=True,
    )
    return session["url"]


def create_billing_portal_session(*, customer_id: str) -> str:
    """Returns a one-time URL to Stripe's hosted billing portal."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=settings.STRIPE_PORTAL_RETURN_URL
    )
    return session["url"]


def verify_webhook(payload: bytes, signature: str) -> dict:
    """
    Verify a Stripe webhook signature and return the event dict.
    Raises stripe.error.SignatureVerificationError on bad signatures.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return stripe.Webhook.construct_event(
        payload=payload, sig_header=signature, secret=settings.STRIPE_WEBHOOK_SECRET
    )
