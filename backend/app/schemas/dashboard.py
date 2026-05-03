"""Dashboard read shapes."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class LocationOut(ORMModel):
    id: UUID
    label: str
    latitude: float
    longitude: float
    timezone: Optional[str] = None
    is_active: bool


class CalibratedOut(ORMModel):
    id: UUID
    location_id: UUID
    observed_at: datetime
    commitment_probability: float
    expected_lead_hours: Optional[float]
    event_type_calibrated: Optional[str]
    confidence: float
    lifecycle_state: str
    explanation: Optional[str] = None
    recommended_action: Optional[str] = None
    storm_transition_score: Optional[float] = None
    stability: Optional[float] = None
    reliability: Optional[float] = None
    phase_prob_entropy: Optional[float] = None
    tier: Optional[str] = None
    action_headline: Optional[str] = None
    action_caveat: Optional[str] = None


class StructuralEventOut(ORMModel):
    id: UUID
    location_id: UUID
    observed_at: datetime
    lifecycle_state: str
    event_type: Optional[str]


class DashboardSnapshot(BaseModel):
    location: LocationOut
    current: Optional[CalibratedOut]
    timeline: List[StructuralEventOut]
    forecast_horizon: List[CalibratedOut]
    model_version: Optional[str] = None
    disclaimer: str

    model_config = {
        "protected_namespaces": ()
    }


class ExecutiveOverviewItem(BaseModel):
    location: LocationOut
    current: Optional[CalibratedOut]


class ExecutiveOverview(BaseModel):
    items: List[ExecutiveOverviewItem]
    model_version: Optional[str] = None
    disclaimer: str

    model_config = {
        "protected_namespaces": ()
    }
