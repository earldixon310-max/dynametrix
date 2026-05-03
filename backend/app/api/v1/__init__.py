"""v1 router aggregator."""
from fastapi import APIRouter

from app.api.v1 import (
    auth, onboarding, billing, dashboard, alerts, reports, audit, admin, locations,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
