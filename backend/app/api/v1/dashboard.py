"""
Dashboard endpoints. Every read filters by the caller's customer_id.

GET /dashboard/overview                 — executive summary across all locations
GET /dashboard/{location_id}            — current state + timeline + horizon
POST /dashboard/{location_id}/refresh   — kick off pipeline (analyst+)
"""
from datetime import timedelta, date, datetime, timezone
import math
import statistics


from collections import Counter
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_analyst, require_viewer
from app.db.models import (
    AuditAction, CalibratedOutput, Location, ModelVersion, StructuralEvent,
)
from app.db.session import get_db
from app.deps import AuthenticatedUser, require_active_subscription
from app.schemas.dashboard import (
    CalibratedOut, DashboardSnapshot, ExecutiveOverview, ExecutiveOverviewItem,
    LocationOut, StructuralEventOut,
)
from app.services import audit
from app.services.storm_reports import ingest_for_date as _ingest_storm_reports
from app.utils.copy import DISCLAIMER_LONG
from app.workers.tasks import run_pipeline_task
from app.db.models.engine import VerificationOutcome, CalibratedOutput, AtmosphericObservation, StructuralEvent

from fastapi import Depends
from sqlalchemy.orm import Session

from app.deps import get_db



router = APIRouter()

# ---------------------------------------------------------------------------
# Derived metrics computed from recent CalibratedOutput history.
# These read from the last N records for a location and produce values in
# [0, 1] suitable for the ingredients and confidence-breakdown panels.
# ---------------------------------------------------------------------------

# Lifecycle states recognized by the system. Keep this aligned with the
# enum used by CalibratedOutput.lifecycle_state.
_LIFECYCLE_STATES = (
    "quiet",
    "pre_commitment",
    "commitment",
    "reconfiguration",
    "decay",
)


def _compute_stability(recent_probs: List[float]) -> Optional[float]:
    """Return [0,1] stability based on inverted, normalized variance.

    Variance of values in [0,1] is bounded above by 0.25 (achieved by a
    perfectly alternating 0/1 sequence). We normalize against that cap so
    a calm signal returns ~1.0 and a wildly oscillating one returns ~0.0.
    Requires at least 3 samples; otherwise we return None to keep the UI
    honest about insufficient history.
    """
    if len(recent_probs) < 3:
        return None
    var = statistics.variance(recent_probs)
    normalized = min(var / 0.25, 1.0)
    return max(0.0, 1.0 - normalized)


def _compute_reliability(recent_probs: List[float]) -> Optional[float]:
    """Return [0,1] reliability based on lag-1 autocorrelation.

    High autocorrelation means recent values predict the next one well —
    the signal is consistent over time. We rescale rho from [-1,1] to
    [0,1] so 0.5 is the neutral 'no signal' point.
    Requires at least 4 samples; otherwise None.
    """
    n = len(recent_probs)
    if n < 4:
        return None
    mean = sum(recent_probs) / n
    num = sum(
        (recent_probs[i] - mean) * (recent_probs[i + 1] - mean)
        for i in range(n - 1)
    )
    denom = sum((p - mean) ** 2 for p in recent_probs)
    if denom == 0:
        # No variance at all in window: signal is flat. Treat as neutral
        # rather than perfectly reliable, since flat could also mean
        # 'pipeline producing identical outputs'.
        return 0.5
    rho = num / denom  # in [-1, 1]
    return max(0.0, min(1.0, (rho + 1) / 2))


def _compute_phase_entropy(recent_states: List[str]) -> Optional[float]:
    """Return [0,1] Shannon entropy of recent lifecycle-state distribution.

    0 = phase is fully resolved (one state the whole window).
    1 = phase is maximally uncertain (uniform across all known states).
    Requires at least 3 samples.
    """
    if len(recent_states) < 3:
        return None
    counts = Counter(recent_states)
    total = sum(counts.values())
    if total == 0:
        return None
    probs = [c / total for c in counts.values()]
    H = -sum(p * math.log(p) for p in probs if p > 0)
    max_H = math.log(len(_LIFECYCLE_STATES))
    if max_H == 0:
        return 0.0
    return max(0.0, min(1.0, H / max_H))

def _model_version(db: Session) -> str | None:
    mv = db.scalar(select(ModelVersion).where(ModelVersion.is_default.is_(True)))
    return mv.version if mv else None

# ---------------------------------------------------------------------------
# Tiered action guidance.
#
# Maps commitment probability into operational tiers (PRD P0-10) and
# returns escalating recommended actions. Tier thresholds are defaults;
# they should eventually be calibrated against verification data per
# event class. Until then, document them clearly here.
#
#   QUIET     prob < 0.30   no structural action required
#   MONITOR   0.30 - 0.50   maintain readiness, prepare team
#   ELEVATED  0.50 - 0.70   initiate response posture
#   IMMINENT  prob >= 0.70  activate response, coordinate with EM
#
# Low-confidence signal at any non-quiet tier carries an extra caveat.
# ---------------------------------------------------------------------------

_TIER_QUIET = "QUIET"
_TIER_MONITOR = "MONITOR"
_TIER_ELEVATED = "ELEVATED"
_TIER_IMMINENT = "IMMINENT"

_TIER_GUIDANCE = {
    _TIER_QUIET: {
        "headline": "No action required",
        "action": (
            "No meaningful structural organization detected. "
            "Continue routine monitoring."
        ),
    },
    _TIER_MONITOR: {
        "headline": "Maintain readiness",
        "action": (
            "Watch for organizing structure. Review forecast products "
            "and brief the team on the developing scenario. No protective "
            "action required at this time."
        ),
    },
    _TIER_ELEVATED: {
        "headline": "Initiate response posture",
        "action": (
            "Structural commitment is increasing. Notify operations "
            "partners and prepare protective actions for the expected "
            "lead-time window. Reassess with each pipeline update."
        ),
    },
    _TIER_IMMINENT: {
        "headline": "Activate response",
        "action": (
            "Structural commitment is high. Coordinate with emergency "
            "management partners and begin executing protective actions. "
            "Defer non-essential operations until the system stabilizes."
        ),
    },
}

_LOW_CONFIDENCE_CAVEAT = (
    "Confidence in this signal is currently low. Cross-check against "
    "official forecast products before acting on this guidance."
)


def _tier_for(probability: Optional[float]) -> str:
    """Map commitment probability to an operational tier."""
    if probability is None:
        return _TIER_QUIET
    if probability >= 0.7:
        return _TIER_IMMINENT
    if probability >= 0.5:
        return _TIER_ELEVATED
    if probability >= 0.3:
        return _TIER_MONITOR
    return _TIER_QUIET


def _guidance_for(
    probability: Optional[float],
    confidence: Optional[float],
) -> dict:
    """Return tier + action headline + action body + optional caveat."""
    tier = _tier_for(probability)
    base = _TIER_GUIDANCE[tier]

    caveat: Optional[str] = None
    if (
        confidence is not None
        and confidence < 0.4
        and tier != _TIER_QUIET
    ):
        caveat = _LOW_CONFIDENCE_CAVEAT

    return {
        "tier": tier,
        "headline": base["headline"],
        "action": base["action"],
        "caveat": caveat,
    }

def _to_calibrated(
    co: CalibratedOutput,
    db: Optional[Session] = None,
    history_window: int = 10,
) -> CalibratedOut:
    """Convert a CalibratedOutput row to a CalibratedOut response model.

    When `db` is provided, derived metrics (stability, reliability,
    phase_prob_entropy) are computed from the last `history_window`
    records for this location. Without `db`, those fields fall back
    to whatever is stored on the row itself (currently None).
    """
    stability: Optional[float] = getattr(co, "stability", None)
    reliability: Optional[float] = getattr(co, "reliability", None)
    phase_entropy: Optional[float] = getattr(co, "phase_prob_entropy", None)
    transition_score: Optional[float] = getattr(co, "storm_transition_score", None)

    if db is not None:
        # Pull the most recent N records for this location, oldest-first.
        recent = list(
            db.scalars(
                select(CalibratedOutput)
                .where(CalibratedOutput.location_id == co.location_id)
                .order_by(CalibratedOutput.observed_at.desc())
                .limit(history_window)
            )
        )
        recent.reverse()  # chronological order

        recent_probs = [
            r.commitment_probability
            for r in recent
            if r.commitment_probability is not None
        ]
        recent_states = [
            (r.lifecycle_state.value if hasattr(r.lifecycle_state, "value") else r.lifecycle_state)
            for r in recent
            if r.lifecycle_state is not None
        ]

        # Only override with computed values if we got something back.
        s = _compute_stability(recent_probs)
        if s is not None:
            stability = s

        r = _compute_reliability(recent_probs)
        if r is not None:
            reliability = r

        e = _compute_phase_entropy(recent_states)
        if e is not None:
            phase_entropy = e

        # Storm transition score: until you have a dedicated signal for
        # this, use the latest commitment probability as a proxy. Replace
        # this line when you wire up a real transition metric.
        if transition_score is None and co.commitment_probability is not None:
            transition_score = co.commitment_probability

    guidance = _guidance_for(co.commitment_probability, co.confidence)

    return CalibratedOut(
        id=co.id,
        location_id=co.location_id,
        observed_at=co.observed_at,
        commitment_probability=co.commitment_probability,
        expected_lead_hours=co.expected_lead_hours,
        event_type_calibrated=(co.event_type_calibrated.value if co.event_type_calibrated else None),
        confidence=co.confidence,
        lifecycle_state=(co.lifecycle_state.value if hasattr(co.lifecycle_state, "value") else co.lifecycle_state),
        explanation=co.explanation,
        recommended_action=guidance["action"],
        tier=guidance["tier"],
        action_headline=guidance["headline"],
        action_caveat=guidance["caveat"],
        storm_transition_score=transition_score,
        stability=stability,
        reliability=reliability,
        phase_prob_entropy=phase_entropy,
        
    )


def _to_event(ev: StructuralEvent) -> StructuralEventOut:
    return StructuralEventOut(
        id=ev.id, location_id=ev.location_id, observed_at=ev.observed_at,
        lifecycle_state=(ev.lifecycle_state.value if hasattr(ev.lifecycle_state, "value") else ev.lifecycle_state),
        event_type=(ev.event_type.value if ev.event_type else None),
    )


@router.get("/overview", response_model=ExecutiveOverview)
def overview(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    require_viewer()  # role gate handled separately when needed; subscription gate above
    locations = list(db.scalars(select(Location).where(Location.customer_id == current_user.customer_id)))

    items: List[ExecutiveOverviewItem] = []
    for loc in locations:
        latest = db.scalar(
            select(CalibratedOutput)
            .where(CalibratedOutput.location_id == loc.id)
            .order_by(CalibratedOutput.observed_at.desc())
        )
        items.append(ExecutiveOverviewItem(
            location=LocationOut.model_validate(loc),
            current=(_to_calibrated(latest, db) if latest else None),
        ))

    return ExecutiveOverview(items=items, model_version=_model_version(db), disclaimer=DISCLAIMER_LONG)


@router.get("/{location_id}", response_model=DashboardSnapshot)
def location_snapshot(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    loc = db.get(Location, location_id)
    if not loc or loc.customer_id != current_user.customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")

    current = db.scalar(
        select(CalibratedOutput)
        .where(CalibratedOutput.location_id == loc.id)
        .order_by(CalibratedOutput.observed_at.desc())
    )
    timeline = list(db.scalars(
        select(StructuralEvent)
        .where(StructuralEvent.location_id == loc.id)
        .order_by(StructuralEvent.observed_at.desc())
        .limit(50)
    ))
    horizon = list(db.scalars(
        select(CalibratedOutput)
        .where(CalibratedOutput.location_id == loc.id,
               CalibratedOutput.observed_at >= (current.observed_at - timedelta(hours=72) if current else None))
        .order_by(CalibratedOutput.observed_at.asc())
        .limit(96)
    )) if current else []

    return DashboardSnapshot(
        location=LocationOut.model_validate(loc),
        current=(_to_calibrated(current, db) if current else None),
        timeline=[_to_event(e) for e in timeline],
        forecast_horizon=[_to_calibrated(c) for c in horizon],
        model_version=_model_version(db),
        disclaimer=DISCLAIMER_LONG,
    )


@router.post("/{location_id}/refresh", status_code=202)
def refresh(
    location_id: UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_analyst()),
):
    loc = db.get(Location, location_id)
    if not loc or loc.customer_id != current_user.customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")

    audit.record(
        db, action=AuditAction.DATA_REFRESH,
        customer_id=current_user.customer_id, user_id=current_user.id, location_id=loc.id,
        model_version=_model_version(db),
    )
    db.commit()

    # Use background task for dev; switch to .delay() to push onto Celery for prod.
    background.add_task(
        run_pipeline_task,
        str(loc.customer_id), str(loc.id), str(current_user.id),
    )
    return {"status": "accepted"}

@router.get("/locations/{location_id}/trajectory")
def get_location_trajectory(location_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(CalibratedOutput)
        .filter(CalibratedOutput.location_id == location_id)
        .order_by(CalibratedOutput.observed_at.desc())
        .limit(20)
        .all()
    )

    seen = set()
    unique = []

    for r in rows:
        key = r.observed_at.isoformat()
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
        if len(unique) >= 5:
            break

    unique.reverse()

    return [
        {
            "label": r.observed_at.strftime("%H:%M"),
            "probability": float(r.commitment_probability or 0),
            "state": r.lifecycle_state.value
            if hasattr(r.lifecycle_state, "value")
            else str(r.lifecycle_state),
        }
        for r in unique
    ]

@router.get("/locations/{location_id}/trajectory")
def get_location_trajectory(location_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(CalibratedOutput)
        .filter(CalibratedOutput.location_id == location_id)
        .order_by(CalibratedOutput.observed_at.desc())
        .limit(5)
        .all()
    )

    rows.reverse()

# ---------------------------------------------------------------------------
# Verification: storm reports ingestion (admin-only)
# ---------------------------------------------------------------------------


@router.post("/admin/ingest-storm-reports")
def ingest_storm_reports(
    target_date: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    """Manually trigger SPC storm-reports ingestion for one UTC date.

    Accepts target_date as YYYY-MM-DD. Returns a per-type summary
    of fetched/created/skipped counts.

    Stage 2a: this is the manual trigger. Stage 2b will schedule
    daily ingestion automatically via Celery.
    """
    try:
        report_date = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="target_date must be YYYY-MM-DD (e.g. 2026-04-27)",
        )

    summary = _ingest_storm_reports(db, report_date)
    return summary

# ---------------------------------------------------------------------------
# Verification: backfill outcomes against ground truth (admin-only)
# ---------------------------------------------------------------------------


@router.post("/admin/backfill-verification")
def backfill_verification(
    decision_threshold: float = 0.5,
    search_radius_km: float = 50.0,
    default_window_hours: float = 24.0,
    limit: int | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    """Run the verification engine over predictions whose window has closed.

    Joins each unverified CalibratedOutput against ground_truth_events
    within search_radius_km of the prediction's location and within
    the prediction's lead-time window. Writes verification_outcomes rows.

    Parameters (query string):
      decision_threshold:  probability cutoff for binary classification.
                           Default 0.5. Re-running with a different value
                           creates a parallel set of outcomes; existing
                           rows are not modified.
      search_radius_km:    matching radius around the prediction location.
                           Default 50 km.
      default_window_hours: fallback lead-time window when a prediction's
                           expected_lead_hours is null. Default 24 hours.
      limit:               cap on number of predictions to process per call,
                           for safety on first runs. Omit for unbounded.

    Returns a counts dict including: examined, newly_verified, already_verified,
    skipped_window_open, skipped_missing_data, plus per-outcome totals
    (hit, miss, false_alarm, correct_negative).
    """
    if not 0.0 <= decision_threshold <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="decision_threshold must be between 0.0 and 1.0",
        )
    if search_radius_km <= 0.0:
        raise HTTPException(
            status_code=400,
            detail="search_radius_km must be positive",
        )
    if default_window_hours <= 0.0:
        raise HTTPException(
            status_code=400,
            detail="default_window_hours must be positive",
        )
    if limit is not None and limit <= 0:
        raise HTTPException(
            status_code=400,
            detail="limit must be a positive integer or omitted",
        )

    from app.services.verification_engine import backfill_verification_outcomes

    summary = backfill_verification_outcomes(
        db,
        decision_threshold=decision_threshold,
        search_radius_km=search_radius_km,
        default_window_hours=default_window_hours,
        limit=limit,
    )
    return summary

# ---------------------------------------------------------------------------
# Verification: aggregate metrics endpoint
# ---------------------------------------------------------------------------


@router.get("/verification/metrics")
def verification_metrics(
    location_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    decision_threshold: float = 0.5,
    n_bins: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    """Aggregate verification metrics from verification_outcomes.

    Filters (all optional):
      location_id:  UUID of a single location. If omitted, aggregates
                    across all locations belonging to the customer.
      start_date:   ISO date (YYYY-MM-DD) lower bound on window_start.
      end_date:     ISO date (YYYY-MM-DD) upper bound on window_start.
      decision_threshold: must match the threshold the outcomes were
                    evaluated against. Default 0.5.
      n_bins:       number of bins for the reliability diagram. Default 10.

    Returns the full summarize() output: counts, POD/FAR/CSI with Wilson
    confidence intervals, Brier score, Brier skill score against
    climatology, base rate, and reliability bins.

    Customer-scoped: only outcomes for locations belonging to the
    requesting user's customer are aggregated.
    """
    from app.services.verification import summarize

    if not 0.0 <= decision_threshold <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="decision_threshold must be between 0.0 and 1.0",
        )
    if n_bins <= 0:
        raise HTTPException(
            status_code=400,
            detail="n_bins must be a positive integer",
        )

    # Customer-scope via Location join, plus threshold filter.
    query = (
        select(VerificationOutcome)
        .join(Location, VerificationOutcome.location_id == Location.id)
        .where(
            Location.customer_id == current_user.customer_id,
            VerificationOutcome.decision_threshold == decision_threshold,
        )
    )

    if location_id:
        try:
            loc_uuid = UUID(location_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="location_id must be a valid UUID",
            )
        query = query.where(VerificationOutcome.location_id == loc_uuid)

    if start_date:
        try:
            sd = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="start_date must be YYYY-MM-DD",
            )
        query = query.where(VerificationOutcome.window_start >= sd)

    if end_date:
        try:
            ed = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="end_date must be YYYY-MM-DD",
            )
        query = query.where(VerificationOutcome.window_start <= ed)

    outcomes = list(db.scalars(query))
    predictions = [(o.predicted_probability, o.observed) for o in outcomes]

    summary = summarize(predictions, threshold=decision_threshold, n_bins=n_bins)

    return {
        "filters": {
            "location_id": location_id,
            "start_date": start_date,
            "end_date": end_date,
            "decision_threshold": decision_threshold,
            "n_bins": n_bins,
        },
        **summary,
    }

# ---------------------------------------------------------------------------
# Atmospheric ingestion: pull Open-Meteo data for one or all locations
# ---------------------------------------------------------------------------


@router.post("/admin/ingest-atmospheric")
def ingest_atmospheric(
    location_id: str | None = None,
    past_days: int = 2,
    forecast_days: int = 1,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    """Manually trigger Open-Meteo atmospheric ingestion.

    Parameters (query string):
      location_id:    UUID of a single location to ingest. If omitted,
                      ingests for every location belonging to the customer.
      past_days:      how many days back from today to fetch. Default 2.
      forecast_days:  how many days forward from today to fetch. Default 1.

    Returns a list of per-location summaries with fetched/created/skipped
    counts, or an error message per location if its fetch failed.
    """
    if past_days < 0 or past_days > 30:
        raise HTTPException(
            status_code=400,
            detail="past_days must be between 0 and 30",
        )
    if forecast_days < 0 or forecast_days > 16:
        raise HTTPException(
            status_code=400,
            detail="forecast_days must be between 0 and 16",
        )

    from app.services.atmospheric_ingestion import ingest_for_location

    if location_id:
        try:
            loc_uuid = UUID(location_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="location_id must be a valid UUID",
            )

        location = db.scalar(
            select(Location).where(
                Location.id == loc_uuid,
                Location.customer_id == current_user.customer_id,
            )
        )
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        summary = ingest_for_location(db, location, past_days, forecast_days)
        return {"summaries": [summary]}

    # No location filter — ingest for every customer-owned location.
    locations = list(
        db.scalars(
            select(Location).where(
                Location.customer_id == current_user.customer_id
            )
        )
    )
    summaries = []
    for loc in locations:
        try:
            summary = ingest_for_location(db, loc, past_days, forecast_days)
            summaries.append(summary)
        except Exception as exc:
            summaries.append(
                {
                    "location_id": str(loc.id),
                    "label": loc.label,
                    "error": str(exc),
                }
            )

    return {"summaries": summaries}

# ---------------------------------------------------------------------------
# Atmospheric: read latest observation for one location
# ---------------------------------------------------------------------------


@router.get("/atmospheric/{location_id}")
def atmospheric_observation(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_active_subscription),
):
    """Return the most recent atmospheric observation for a location.

    Customer-scoped: the location must belong to the calling customer.
    Returns null `observation` when no atmospheric data has been
    ingested yet for that location.
    """
    try:
        loc_uuid = UUID(location_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="location_id must be a valid UUID",
        )

    location = db.scalar(
        select(Location).where(
            Location.id == loc_uuid,
            Location.customer_id == current_user.customer_id,
        )
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    now_utc = datetime.now(timezone.utc)
    latest = db.scalar(
        select(AtmosphericObservation)
        .where(
            AtmosphericObservation.location_id == loc_uuid,
            AtmosphericObservation.observed_at <= now_utc,
        )
        .order_by(AtmosphericObservation.observed_at.desc())
    )

    if latest is None:
        return {
            "location_id": str(location.id),
            "label": location.label,
            "observation": None,
        }

    return {
        "location_id": str(location.id),
        "label": location.label,
        "observation": {
            "observed_at": latest.observed_at.isoformat(),
            "source": latest.source,
            "cape": latest.cape,
            "lifted_index": latest.lifted_index,
            "convective_inhibition": latest.convective_inhibition,
            "temperature_2m": latest.temperature_2m,
            "dewpoint_2m": latest.dewpoint_2m,
            "relative_humidity_2m": latest.relative_humidity_2m,
            "pressure_msl": latest.pressure_msl,
            "wind_speed_10m": latest.wind_speed_10m,
            "wind_direction_10m": latest.wind_direction_10m,
            "wind_speed_80m": latest.wind_speed_80m,
            "wind_direction_80m": latest.wind_direction_80m,
        },
    }

    result = []

    for r in unique:
        ci = float(r.confidence or 0)
        stability = float(getattr(r, "stability", 0) or 0)
        reliability = float(getattr(r, "reliability", 0) or 0)

        persistence = (stability + reliability + ci) / 3.0
        coherence_energy = ci  # proxy for now
        trajectory_velocity = abs(coherence_energy - persistence)

        result.append({
            "label": r.observed_at.strftime("%H:%M"),
            "probability": float(r.commitment_probability or 0),
            "state": r.lifecycle_state.value if hasattr(r.lifecycle_state, "value") else str(r.lifecycle_state),
            "persistence": persistence,
            "coherence_energy": coherence_energy,
            "trajectory_velocity": trajectory_velocity,
        })

    return result