"""Verification engine: join predictions against ground truth.

Database-coupled functions that take CalibratedOutput rows and
ground_truth_events rows and produce verification_outcomes rows.

Design choices for falsifiability:
- Each outcome is keyed by (calibrated_output_id, decision_threshold).
  Re-evaluating the same prediction at a different threshold creates
  a new row, not an overwrite. History is preserved.
- Predictions whose evaluation window has not yet closed are skipped.
  We only score outcomes when the answer is actually knowable.
- Predictions with null commitment_probability are skipped.
- The engine never edits its inputs. CalibratedOutput rows and
  ground_truth_events rows are read-only from this module's view.

The pure scoring math (POD, FAR, CSI, Brier, reliability_bins) lives
in app.services.verification and is intentionally separate so it can
be tested without database fixtures.
"""

import logging
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import CalibratedOutput, Location
from app.db.models.engine import GroundTruthEvent, VerificationOutcome
from app.services.verification import (
    OUTCOME_CORRECT_NEGATIVE,
    OUTCOME_FALSE_ALARM,
    OUTCOME_HIT,
    OUTCOME_MISS,
    classify_outcome,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geographic distance — haversine great-circle formula
# ---------------------------------------------------------------------------


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometers.

    Uses the haversine formula, which is accurate to within ~0.5%
    for typical Earth distances. Sufficient for verification radius
    matching where 50km vs 50.2km doesn't change outcome classification.
    """
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi / 2.0) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2.0) ** 2
    c = 2.0 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Tier mapping (kept aligned with dashboard.py)
# ---------------------------------------------------------------------------


def _tier_for(probability: Optional[float]) -> str:
    if probability is None:
        return "QUIET"
    if probability >= 0.7:
        return "IMMINENT"
    if probability >= 0.5:
        return "ELEVATED"
    if probability >= 0.3:
        return "MONITOR"
    return "QUIET"


# ---------------------------------------------------------------------------
# Event matching
# ---------------------------------------------------------------------------


def find_matching_events(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
    window_start: datetime,
    window_end: datetime,
) -> List[Tuple[GroundTruthEvent, float]]:
    """Return ground truth events within radius and time window.

    Two-stage filter: first a cheap bounding-box query at the database
    level to limit candidates, then exact haversine distance computed
    in Python for the candidates. Returns a list of (event, distance_km)
    tuples sorted by distance.
    """
    if radius_km <= 0:
        return []

    # Bounding-box buffer in degrees. 1 degree latitude ~= 111 km.
    # Longitude varies with latitude; we use the worst case (cosine of
    # the prediction's latitude) for the longitude buffer.
    lat_buffer = radius_km / 111.0
    cos_lat = max(cos(radians(latitude)), 0.01)  # guard near poles
    lon_buffer = radius_km / (111.0 * cos_lat)

    candidates = list(
        db.scalars(
            select(GroundTruthEvent).where(
                GroundTruthEvent.event_at >= window_start,
                GroundTruthEvent.event_at <= window_end,
                GroundTruthEvent.latitude.between(
                    latitude - lat_buffer, latitude + lat_buffer
                ),
                GroundTruthEvent.longitude.between(
                    longitude - lon_buffer, longitude + lon_buffer
                ),
            )
        )
    )

    matches: List[Tuple[GroundTruthEvent, float]] = []
    for event in candidates:
        dist = haversine_km(latitude, longitude, event.latitude, event.longitude)
        if dist <= radius_km:
            matches.append((event, dist))

    matches.sort(key=lambda pair: pair[1])
    return matches


# ---------------------------------------------------------------------------
# Single-prediction evaluation
# ---------------------------------------------------------------------------


def evaluate_prediction(
    db: Session,
    prediction: CalibratedOutput,
    *,
    decision_threshold: float = 0.5,
    search_radius_km: float = 50.0,
    default_window_hours: float = 24.0,
    now_utc: Optional[datetime] = None,
) -> Optional[VerificationOutcome]:
    """Evaluate one prediction against ground truth, write a VerificationOutcome.

    Returns the outcome row (newly created or pre-existing for the same
    (prediction, threshold) pair). Returns None if the prediction is not
    yet evaluable (window not closed, missing probability, missing location).
    """
    if prediction.commitment_probability is None:
        return None

    location = db.get(Location, prediction.location_id)
    if location is None:
        return None
    if location.latitude is None or location.longitude is None:
        return None

    lead_hours = prediction.expected_lead_hours
    if lead_hours is None or lead_hours <= 0:
        lead_hours = default_window_hours

    window_start = prediction.observed_at
    window_end = prediction.observed_at + timedelta(hours=float(lead_hours))

    now = now_utc or datetime.now(timezone.utc)
    if window_end > now:
        # Window has not closed yet — outcome is still unknown.
        return None

    # Idempotency: short-circuit if already evaluated at this threshold.
    existing = db.scalar(
        select(VerificationOutcome).where(
            VerificationOutcome.calibrated_output_id == prediction.id,
            VerificationOutcome.decision_threshold == decision_threshold,
        )
    )
    if existing is not None:
        return existing

    matches = find_matching_events(
        db,
        latitude=location.latitude,
        longitude=location.longitude,
        radius_km=search_radius_km,
        window_start=window_start,
        window_end=window_end,
    )

    observed = len(matches) > 0
    matched_event = matches[0][0] if matches else None

    predicted_prob = float(prediction.commitment_probability)
    outcome_label = classify_outcome(predicted_prob, observed, decision_threshold)
    tier = _tier_for(predicted_prob)

    row = {
        "calibrated_output_id": prediction.id,
        "location_id": prediction.location_id,
        "matched_event_id": matched_event.id if matched_event else None,
        "predicted_probability": predicted_prob,
        "tier_at_prediction": tier,
        "decision_threshold": decision_threshold,
        "window_start": window_start,
        "window_end": window_end,
        "search_radius_km": search_radius_km,
        "observed": observed,
        "outcome": outcome_label,
    }

    stmt = insert(VerificationOutcome).values(row)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["calibrated_output_id", "decision_threshold"]
    )
    stmt = stmt.returning(VerificationOutcome.id)
    result = db.execute(stmt)
    db.commit()

    inserted_id = result.scalar_one_or_none()
    if inserted_id is None:
        # A concurrent writer beat us; re-query.
        return db.scalar(
            select(VerificationOutcome).where(
                VerificationOutcome.calibrated_output_id == prediction.id,
                VerificationOutcome.decision_threshold == decision_threshold,
            )
        )

    return db.get(VerificationOutcome, inserted_id)


# ---------------------------------------------------------------------------
# Bulk backfill
# ---------------------------------------------------------------------------


def backfill_verification_outcomes(
    db: Session,
    *,
    decision_threshold: float = 0.5,
    search_radius_km: float = 50.0,
    default_window_hours: float = 24.0,
    limit: Optional[int] = None,
    now_utc: Optional[datetime] = None,
) -> dict:
    """Process all predictions whose window has closed and that lack
    a verification outcome at this threshold. Returns counts.
    """
    now = now_utc or datetime.now(timezone.utc)

    # Predictions whose lead window has already closed.
    # We treat null lead time as default_window_hours for window math.
    query = select(CalibratedOutput).where(
        CalibratedOutput.commitment_probability.is_not(None),
    )
    if limit is not None:
        query = query.limit(limit)

    predictions = list(db.scalars(query))

    counts = {
        "examined": 0,
        "skipped_window_open": 0,
        "skipped_missing_data": 0,
        "already_verified": 0,
        "newly_verified": 0,
        OUTCOME_HIT: 0,
        OUTCOME_MISS: 0,
        OUTCOME_FALSE_ALARM: 0,
        OUTCOME_CORRECT_NEGATIVE: 0,
    }

    for pred in predictions:
        counts["examined"] += 1

        # Was this prediction already evaluated at this threshold?
        existing = db.scalar(
            select(VerificationOutcome).where(
                VerificationOutcome.calibrated_output_id == pred.id,
                VerificationOutcome.decision_threshold == decision_threshold,
            )
        )
        if existing is not None:
            counts["already_verified"] += 1
            counts[existing.outcome] = counts.get(existing.outcome, 0) + 1
            continue

        outcome = evaluate_prediction(
            db,
            pred,
            decision_threshold=decision_threshold,
            search_radius_km=search_radius_km,
            default_window_hours=default_window_hours,
            now_utc=now,
        )

        if outcome is None:
            # Either window still open or missing data.
            lead_hours = pred.expected_lead_hours or default_window_hours
            if pred.observed_at + timedelta(hours=float(lead_hours)) > now:
                counts["skipped_window_open"] += 1
            else:
                counts["skipped_missing_data"] += 1
            continue

        counts["newly_verified"] += 1
        counts[outcome.outcome] = counts.get(outcome.outcome, 0) + 1

    return counts