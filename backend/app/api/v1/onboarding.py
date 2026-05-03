"""
Customer onboarding flow.

The signed-in user's email becomes the primary contact and an admin role on
the new customer record. The flow:

  1. POST /onboarding              → creates Customer + Locations + AlertSetting
                                     + a pending Subscription (status=incomplete)
  2. POST /billing/checkout        → returns Stripe checkout URL for chosen plan
  3. (Stripe webhook updates Subscription.status to active/trialing)
  4. Dashboard becomes accessible.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    AlertSetting, Customer, CustomerUser, Location,
    Subscription, SubscriptionStatus,
)
from app.db.session import get_db
from app.deps import AuthenticatedUser, get_current_user
from app.schemas.onboarding import OnboardingPayload

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def complete_onboarding(
    payload: OnboardingPayload,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if current_user.customer_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User is already associated with a customer; onboarding can only run once.",
        )

    customer = Customer(
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        billing_address_line1=payload.billing_address_line1,
        billing_address_line2=payload.billing_address_line2,
        billing_city=payload.billing_city,
        billing_region=payload.billing_region,
        billing_postal_code=payload.billing_postal_code,
        billing_country=payload.billing_country,
        terms_accepted_at=datetime.now(timezone.utc),
        onboarding_completed_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(customer)
    db.flush()

    db.add(CustomerUser(customer_id=customer.id, user_id=current_user.id, role="admin"))

    for loc in payload.locations:
        db.add(Location(
            customer_id=customer.id,
            label=loc.label, address=loc.address,
            latitude=loc.latitude, longitude=loc.longitude,
            timezone=loc.timezone, is_active=True,
        ))

    prefs = payload.alert_preferences
    db.add(AlertSetting(
        customer_id=customer.id, location_id=None,
        email_enabled=prefs.email_enabled,
        email_recipients=[str(e) for e in prefs.email_recipients],
        webhook_enabled=prefs.webhook_enabled,
        webhook_url=prefs.webhook_url,
        webhook_secret=prefs.webhook_secret,
        confidence_threshold=prefs.confidence_threshold,
        cooldown_minutes=prefs.cooldown_minutes,
        enabled_event_types=prefs.enabled_event_types,
    ))

    db.add(Subscription(
        customer_id=customer.id,
        plan_code=payload.plan,
        status=SubscriptionStatus.INCOMPLETE,
    ))

    db.commit()
    return {"customer_id": str(customer.id), "next": "/billing/checkout"}
