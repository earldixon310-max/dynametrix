"""
Seed script: creates a demo customer, an admin user, an analyst, a viewer,
one location (Newark, NJ), a default model version, an alert setting, and a
trial subscription. Idempotent — safe to re-run.

Usage:
    python -m app.db.seed
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.db.models import (
    Customer, User, CustomerUser,
    Location,
    Subscription, PlanCode, SubscriptionStatus,
    AlertSetting,
    ModelVersion,
)

DEMO_CUSTOMER_EMAIL = "ops@demo.dynametrix.io"
DEMO_USERS = [
    ("admin@demo.dynametrix.io", "Demo Admin", "DemoPass!234", "admin"),
    ("analyst@demo.dynametrix.io", "Demo Analyst", "DemoPass!234", "analyst"),
    ("viewer@demo.dynametrix.io", "Demo Viewer", "DemoPass!234", "viewer"),
]


def get_or_create_customer(db) -> Customer:
    cust = db.scalar(select(Customer).where(Customer.contact_email == DEMO_CUSTOMER_EMAIL))
    if cust:
        return cust
    cust = Customer(
        company_name="Demo Municipality",
        contact_name="Ops Team",
        contact_email=DEMO_CUSTOMER_EMAIL,
        billing_address_line1="100 Main St",
        billing_city="Newark",
        billing_region="NJ",
        billing_postal_code="07102",
        billing_country="US",
        terms_accepted_at=datetime.now(timezone.utc),
        onboarding_completed_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(cust)
    db.flush()
    return cust


def get_or_create_users(db, customer: Customer):
    for email, name, password, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, full_name=name, password_hash=hash_password(password), is_active=True)
            db.add(user)
            db.flush()
        link = db.scalar(
            select(CustomerUser).where(
                CustomerUser.customer_id == customer.id, CustomerUser.user_id == user.id
            )
        )
        if not link:
            db.add(CustomerUser(customer_id=customer.id, user_id=user.id, role=role))


def get_or_create_location(db, customer: Customer) -> Location:
    loc = db.scalar(
        select(Location).where(Location.customer_id == customer.id, Location.label == "Newark HQ")
    )
    if loc:
        return loc
    loc = Location(
        customer_id=customer.id,
        label="Newark HQ",
        address="100 Main St, Newark, NJ 07102",
        latitude=40.7357,
        longitude=-74.1724,
        timezone="America/New_York",
        is_active=True,
    )
    db.add(loc)
    db.flush()
    return loc


def get_or_create_subscription(db, customer: Customer) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.customer_id == customer.id))
    if sub:
        return sub
    sub = Subscription(
        customer_id=customer.id,
        plan_code=PlanCode.TRIAL,
        status=SubscriptionStatus.TRIALING,
    )
    db.add(sub)
    db.flush()
    return sub


def get_or_create_alert_settings(db, customer: Customer):
    existing = db.scalar(
        select(AlertSetting).where(AlertSetting.customer_id == customer.id, AlertSetting.location_id.is_(None))
    )
    if existing:
        return existing
    setting = AlertSetting(
        customer_id=customer.id,
        location_id=None,
        email_enabled=True,
        email_recipients=["ops@demo.dynametrix.io"],
        webhook_enabled=False,
        confidence_threshold=0.65,
        cooldown_minutes=30,
        enabled_event_types=["pre_commitment", "commitment", "reconfiguration"],
    )
    db.add(setting)
    return setting


def get_or_create_model_version(db) -> ModelVersion:
    mv = db.scalar(select(ModelVersion).where(ModelVersion.is_default.is_(True)))
    if mv:
        return mv
    mv = ModelVersion(
        version="calibrator-v1.0",
        description="Initial calibration of MCC/CI/CSO structural signatures.",
        calibrator_path="tools/train_weather_commitment_calibrator.py",
        is_default=True,
        trained_at=datetime.now(timezone.utc),
    )
    db.add(mv)
    return mv


def main() -> None:
    db = SessionLocal()
    try:
        customer = get_or_create_customer(db)
        get_or_create_users(db, customer)
        get_or_create_location(db, customer)
        get_or_create_subscription(db, customer)
        get_or_create_alert_settings(db, customer)
        get_or_create_model_version(db)
        db.commit()
        print("Seed complete.")
        print("Login: admin@demo.dynametrix.io / DemoPass!234")
        print("       analyst@demo.dynametrix.io / DemoPass!234")
        print("       viewer@demo.dynametrix.io / DemoPass!234")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
