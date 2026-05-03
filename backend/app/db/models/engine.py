"""
Engine-side records: pipeline runs, structural events, calibrated outputs, model versions.

Naming uses neutral, non-overclaiming language. Event labels mirror what the
engine emits.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer, 
    Enum as SAEnum, Index, JSON, Boolean, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    UniqueConstraint,
)



class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EventType(str, enum.Enum):
    PRE_COMMITMENT = "pre_commitment"
    COMMITMENT = "commitment"
    RECONFIGURATION = "reconfiguration"
    FALSE_START = "false_start"
    DECAY = "decay"


class LifecycleState(str, enum.Enum):
    QUIET = "quiet"
    ORGANIZING = "organizing"
    PRE_COMMITMENT = "pre_commitment"
    COMMITTED = "committed"
    RECONFIGURING = "reconfiguring"
    DECAYING = "decaying"


class ModelVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1024))
    calibrator_path: Mapped[Optional[str]] = mapped_column(String(512))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PipelineRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_pipeline_runs_customer_id", "customer_id"),
        Index("ix_pipeline_runs_location_id", "location_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    triggered_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="SET NULL")
    )

    status: Mapped[PipelineRunStatus] = mapped_column(
        SAEnum(PipelineRunStatus, name="pipeline_run_status"),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(String(2048))
    rows_processed: Mapped[Optional[int]] = mapped_column(Integer)
    output_csv_path: Mapped[Optional[str]] = mapped_column(String(512))


class StructuralEvent(Base, UUIDMixin, TimestampMixin):
    """A discrete structural state change emitted by the engine."""
    __tablename__ = "structural_events"
    __table_args__ = (
        Index("ix_structural_events_customer_id", "customer_id"),
        Index("ix_structural_events_location_id", "location_id"),
        Index("ix_structural_events_observed_at", "observed_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL")
    )

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        SAEnum(LifecycleState, name="lifecycle_state"), nullable=False
    )
    event_type: Mapped[Optional[EventType]] = mapped_column(SAEnum(EventType, name="event_type"))

    # Raw structural metrics (MCC, CI, CSO derived). Stored as JSON for flexibility.
    structural_metrics: Mapped[Optional[dict]] = mapped_column(JSON)


class CalibratedOutput(Base, UUIDMixin, TimestampMixin):
    """
    The user-facing calibrated output: probability + lead time + event type +
    confidence. One row per (location, observed_at, model_version).
    """
    __tablename__ = "calibrated_outputs"
    __table_args__ = (
        UniqueConstraint(
            "location_id", "observed_at", "model_version_id",
            name="uq_calibrated_output_per_obs"
        ),
        Index("ix_calibrated_outputs_customer_id", "customer_id"),
        Index("ix_calibrated_outputs_location_id", "location_id"),
        Index("ix_calibrated_outputs_observed_at", "observed_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    pipeline_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL")
    )

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    commitment_probability: Mapped[float] = mapped_column(Float, nullable=False)
    expected_lead_hours: Mapped[Optional[float]] = mapped_column(Float)
    event_type_calibrated: Mapped[Optional[EventType]] = mapped_column(
        SAEnum(EventType, name="event_type", create_type=False)
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        SAEnum(LifecycleState, name="lifecycle_state", create_type=False), nullable=False
    )

    # Free-form explanation text generated alongside (kept conservative).
    explanation: Mapped[Optional[str]] = mapped_column(String(2048))
    recommended_action: Mapped[Optional[str]] = mapped_column(String(2048))

    # Use whatever Base your project already declares — usually:
# from app.db.base import Base
# Adjust the import to match your codebase.


class GroundTruthEvent(Base):
    """A verified meteorological event from an authoritative source.

    Sources: NWS local storm reports, NCEI Storm Events Database, or
    later, manual entries. Each row represents one event in space and
    time. Used as the ground truth side of verification.
    """

    __tablename__ = "ground_truth_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(64), nullable=False)
    source_event_id = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=False)
    severity = Column(String(64), nullable=True)
    event_at = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    raw = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        # Idempotent ingestion — same source+id can only appear once.
        UniqueConstraint("source", "source_event_id", name="uq_gte_source"),
        Index("ix_gte_event_at", "event_at"),
        Index("ix_gte_event_type", "event_type"),
        Index("ix_gte_lat_lng", "latitude", "longitude"),
    )


class VerificationOutcome(Base):
    """One verification of a single CalibratedOutput against ground truth.

    Links a prediction to whether (or not) a matching event occurred in
    its evaluation window. The outcome enum is stored as a string for
    portability; valid values: 'hit', 'miss', 'false_alarm',
    'correct_negative'.
    """

    __tablename__ = "verification_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    calibrated_output_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calibrated_outputs.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    matched_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ground_truth_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    predicted_probability = Column(Float, nullable=False)
    tier_at_prediction = Column(String(16), nullable=True)
    decision_threshold = Column(Float, nullable=False, default=0.5)

    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    search_radius_km = Column(Float, nullable=False, default=50.0)

    observed = Column(Boolean, nullable=False)
    outcome = Column(String(32), nullable=False)

    verified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "calibrated_output_id",
            "decision_threshold",
            name="uq_vo_pred_threshold",
        ),
        Index("ix_vo_location_id", "location_id"),
        Index("ix_vo_outcome", "outcome"),
        Index("ix_vo_window", "window_start", "window_end"),
    )

class AtmosphericObservation(Base):
    """Hourly atmospheric ingredients for a location, sourced from a
    real meteorological data feed (initially Open-Meteo).

    These rows are the inputs that, eventually, the pipeline calibrator
    will consume to make commitment probability responsive to actual
    atmospheric reality rather than internal calibrator dynamics.

    Idempotent ingestion: one row per (location, observed_at, source).
    Re-fetching the same hour for the same location updates nothing
    (preserves history); changes from a different source create a
    parallel row.
    """

    __tablename__ = "atmospheric_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source = Column(String(64), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)

    # Severe-weather-relevant diagnostics
    cape = Column(Float, nullable=True)              # J/kg
    lifted_index = Column(Float, nullable=True)      # K (negative is unstable)
    convective_inhibition = Column(Float, nullable=True)  # J/kg

    # Surface state
    temperature_2m = Column(Float, nullable=True)    # °C
    dewpoint_2m = Column(Float, nullable=True)       # °C
    relative_humidity_2m = Column(Float, nullable=True)  # %
    pressure_msl = Column(Float, nullable=True)      # hPa

    # Wind profile (speed in m/s, direction in degrees)
    wind_speed_10m = Column(Float, nullable=True)
    wind_direction_10m = Column(Float, nullable=True)
    wind_speed_80m = Column(Float, nullable=True)
    wind_direction_80m = Column(Float, nullable=True)
    wind_speed_180m = Column(Float, nullable=True)
    wind_direction_180m = Column(Float, nullable=True)

    # Upper-level diagnostics for lapse-rate and shear computations
    temperature_500hPa = Column(Float, nullable=True)
    temperature_700hPa = Column(Float, nullable=True)
    temperature_850hPa = Column(Float, nullable=True)

    # Precipitable water (column-integrated water vapor)
    precipitable_water = Column(Float, nullable=True)  # mm

    precipitation = Column(Float, nullable=True)  # mm in the past hour

    # Raw payload for debugging / future reprocessing without re-fetching
    raw = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "observed_at",
            "source",
            name="uq_atmos_loc_time_source",
        ),
        Index("ix_atmos_location_observed_at", "location_id", "observed_at"),
        Index("ix_atmos_observed_at", "observed_at"),
    )