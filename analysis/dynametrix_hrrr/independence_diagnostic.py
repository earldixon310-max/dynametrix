"""
independence_diagnostic.py

EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.

Computes Pearson correlation of residual errors between Dynametrix v3
and a provisional HRRR-derived probabilistic forecast, to inform the
go/no-go decision on the full Dynametrix-HRRR combination
pre-registration.

Protocol: INDEPENDENCE_DIAGNOSTIC_PROTOCOL.md
Decision rule encoded in §5 (pre-committed thresholds).
Output: DIAGNOSTIC_DYNAMETRIX_HRRR_INDEPENDENCE_<date>.md

This script cannot be cited as confirmatory evidence in any subsequent
published audit. If its findings turn out to be substantively
interesting in their own right, they must be re-derived under proper
AEPF lock discipline before publication.

Usage:
    python independence_diagnostic.py \\
        --window-start 2026-03-01 \\
        --window-end 2026-05-24 \\
        --output diagnostics/DIAGNOSTIC_DYNAMETRIX_HRRR_INDEPENDENCE_2026-05-26.md
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

import numpy as np

# -------------------------------------------------------------------------
# Backend integration — make backend/ importable so we can reach the ORM
# models and verification engine without copying code. This file lives at
# analysis/dynametrix_hrrr/independence_diagnostic.py; repo root is two
# parents up.
# -------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_PATH = _REPO_ROOT / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))

# Backend imports are deferred to inside the stub functions so this file
# can be imported (for unit-testing the pure functions) on a machine that
# does not have the database environment configured.


# =========================================================================
# Configuration constants (LOCKED to protocol §5; do not modify post-run)
# =========================================================================

BOOTSTRAP_B = 1_000
BOOTSTRAP_SEED = 0x1DEA
MIN_LOCATION_HOURS = 200

# Decision rule thresholds (protocol §5)
THRESHOLD_LOW = 0.4   # below this: proceed unconstrained
THRESHOLD_HIGH = 0.7  # above this: do not proceed

# Prospective evaluation window for the full study (exclude from diagnostic)
EVALUATION_WINDOW_START = date(2026, 6, 1)
EVALUATION_WINDOW_END = date(2026, 10, 31)

# Per-category breakdown minimum events (for context only, not for decision)
PER_CATEGORY_MIN_EVENTS = 30

# Provisional HRRR-to-probability transformation parameters (protocol §3)
UH_THRESHOLD_M2_S2 = 25.0
UH_NEIGHBORHOOD_KM = 40.0

# Dynametrix v3 model version string (matches model_versions.version)
DYNAMETRIX_V3_VERSION = "calibrator-v3.0"

# Verification matching radius (protocol §3.3; 100 km matches v3a verification)
VERIFICATION_RADIUS_KM = 100.0

# Default lead-hours fallback when CalibratedOutput.expected_lead_hours is null
# (mirrors verification_engine.evaluate_prediction's default_window_hours)
DEFAULT_LEAD_HOURS = 24.0


# =========================================================================
# Data record type
# =========================================================================

@dataclass
class MatchedRecord:
    """One matched location-hour with both predictions and ground truth."""
    location_id: str
    issue_time: datetime
    valid_time: datetime
    p_dynametrix: float
    p_hrrr: float
    event: int             # 0 or 1, from SPC storm report match
    event_category: str    # 'tornado', 'hail', 'wind', or 'none'


# =========================================================================
# Data loading
# =========================================================================

def load_dynametrix_v3_outputs(
    window_start: date,
    window_end: date,
) -> List[dict]:
    """
    Load all Dynametrix v3 calibrated probability outputs in the window.

    Queries the production `calibrated_outputs` table for rows where the
    model version is `calibrator-v3.0` and `observed_at` falls between
    window_start (inclusive, 00:00:00 UTC) and window_end (inclusive,
    23:59:59.999999 UTC). Joins with the `locations` table to attach
    latitude/longitude needed for downstream HRRR sampling and ground-truth
    matching.

    Each returned record has:
        - location_id (str)        UUID stringified for portability
        - issue_time (datetime)    = observed_at (UTC)
        - valid_time (datetime)    = observed_at + expected_lead_hours
                                     (falls back to DEFAULT_LEAD_HOURS = 24)
        - p_dynametrix (float)     = commitment_probability, in [0, 1]
        - latitude (float)         from Location
        - longitude (float)        from Location
        - expected_lead_hours (float)

    Records with null commitment_probability are excluded at the database
    level so they cannot silently propagate into the residual computation.

    The window MUST exclude the prospective evaluation window
    [EVALUATION_WINDOW_START, EVALUATION_WINDOW_END] per protocol §2.
    Enforcement happens in `_validate_window()` at the entrypoint; this
    function trusts the validation has already passed.
    """
    # Local imports keep the module importable for unit tests without a DB.
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.db.models import CalibratedOutput, Location, ModelVersion

    window_start_dt = datetime.combine(window_start, time.min, tzinfo=timezone.utc)
    window_end_dt = datetime.combine(window_end, time.max, tzinfo=timezone.utc)

    stmt = (
        select(
            CalibratedOutput.location_id,
            CalibratedOutput.observed_at,
            CalibratedOutput.commitment_probability,
            CalibratedOutput.expected_lead_hours,
            Location.latitude,
            Location.longitude,
        )
        .join(ModelVersion, CalibratedOutput.model_version_id == ModelVersion.id)
        .join(Location, CalibratedOutput.location_id == Location.id)
        .where(
            ModelVersion.version == DYNAMETRIX_V3_VERSION,
            CalibratedOutput.observed_at >= window_start_dt,
            CalibratedOutput.observed_at <= window_end_dt,
            CalibratedOutput.commitment_probability.is_not(None),
        )
        .order_by(CalibratedOutput.observed_at)
    )

    records: List[dict] = []
    with SessionLocal() as db:
        for row in db.execute(stmt).all():
            lead_hours = (
                float(row.expected_lead_hours)
                if row.expected_lead_hours is not None and row.expected_lead_hours > 0
                else DEFAULT_LEAD_HOURS
            )
            issue_time = row.observed_at
            # Ensure issue_time is timezone-aware. The schema declares
            # DateTime(timezone=True), but Postgres may return naive
            # datetimes through some drivers; coerce defensively.
            if issue_time.tzinfo is None:
                issue_time = issue_time.replace(tzinfo=timezone.utc)
            valid_time = issue_time + timedelta(hours=lead_hours)
            records.append({
                "location_id": str(row.location_id),
                "issue_time": issue_time,
                "valid_time": valid_time,
                "p_dynametrix": float(row.commitment_probability),
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "expected_lead_hours": lead_hours,
            })
    return records


def load_hrrr_uh_probabilities(records: List[dict]) -> List[dict]:
    """
    For each (location, valid_time) in records, compute the HRRR-derived
    probability via the provisional UH transformation (protocol §3):
        - Source field: HRRR MXUPHL (max updraft helicity, 2-5 km AGL layer)
        - Threshold: UH_THRESHOLD_M2_S2 (25 m²/s²)
        - Neighborhood: UH_NEIGHBORHOOD_KM (40 km radius around location)
        - Normalization: provisional saturating exponential, p = 1 - exp(-3*f)

    Returns the input records, each augmented with a `p_hrrr` field in [0, 1].
    Records for which HRRR is unavailable (archive gap, fetch failure) are
    dropped, with an accounting print for transparency.

    HRRR cycle selection:
        For each record, init_time is the most recent HRRR run at or before
        issue_time (HRRR runs hourly). Forecast hour fxx is the rounded
        delta in hours from init_time to valid_time, clamped to [0, 18]
        (HRRR's standard horizon; extended runs at 00/06/12/18Z reach 48
        but we don't need them here).

    Neighborhood probability formula (provisional):
        f = fraction of HRRR grid cells within UH_NEIGHBORHOOD_KM of the
        location with MXUPHL >= UH_THRESHOLD_M2_S2
        p_hrrr = 1 - exp(-3 * f)
        Calibration check: f=0.2 -> p≈0.451, f=0.5 -> p≈0.777, f=1.0 -> p≈0.950.

    Batching: records are grouped by (init_time, fxx) so each unique HRRR
    cycle is fetched at most once. herbie caches downloads locally
    (default ~/data/herbie) so re-runs are fast.

    Implementation choice: herbie-data with the 'prs' (pressure-level)
    product, searched for the MXUPHL 2000-5000 m AGL layer.
    """
    import math
    from collections import defaultdict
    from herbie import Herbie

    EARTH_RADIUS_KM = 6371.0088

    def vectorized_haversine(lat0: float, lon0: float,
                             lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        """Great-circle distance in km from (lat0, lon0) to arrays (lats, lons)."""
        lat0_r = math.radians(lat0)
        lon0_r = math.radians(lon0)
        lats_r = np.radians(lats)
        lons_r = np.radians(lons)
        dlat = lats_r - lat0_r
        dlon = lons_r - lon0_r
        a = np.sin(dlat / 2.0) ** 2 + np.cos(lat0_r) * np.cos(lats_r) * np.sin(dlon / 2.0) ** 2
        c = 2.0 * np.arcsin(np.sqrt(a))
        return EARTH_RADIUS_KM * c

    def select_hrrr_cycle(issue_time: datetime, valid_time: datetime):
        """Return (init_time, fxx). init_time = top of hour <= issue_time."""
        init_time = issue_time.replace(minute=0, second=0, microsecond=0)
        delta_hours = (valid_time - init_time).total_seconds() / 3600.0
        fxx = int(round(delta_hours))
        fxx = max(0, min(fxx, 18))
        return init_time, fxx

    # Group records by HRRR cycle for batched fetching.
    cycle_to_records: dict = defaultdict(list)
    for rec in records:
        cycle = select_hrrr_cycle(rec["issue_time"], rec["valid_time"])
        cycle_to_records[cycle].append(rec)

    print(f"      Grouped {len(records):,} records into "
          f"{len(cycle_to_records):,} unique HRRR cycles.")

    augmented: List[dict] = []
    cycles_fetched = 0
    cycles_failed = 0
    records_dropped = 0

    # Cache for the HRRR grid lat/lon. The grid is static across cycles, so
    # we only need to compute neighborhood masks per (location, grid) once.
    grid_lats = None
    grid_lons = None
    # Map (location_id) -> boolean mask over flattened grid cells.
    location_masks: dict = {}

    for cycle_idx, ((init_time, fxx), recs) in enumerate(cycle_to_records.items()):
        if cycle_idx % 25 == 0:
            print(f"      [{cycle_idx}/{len(cycle_to_records)}] "
                  f"init={init_time:%Y-%m-%d %H:%MZ} fxx={fxx:02d}")
        try:
            H = Herbie(
                init_time.strftime("%Y-%m-%d %H:%M"),
                model="hrrr",
                product="prs",
                fxx=fxx,
                verbose=False,
            )
            # MXUPHL 2-5 km AGL — the standard supercell/UH signal.
            ds = H.xarray(":MXUPHL:5000-2000 m above ground:")
        except Exception as exc:
            print(f"      WARN: HRRR fetch failed for init={init_time} "
                  f"fxx={fxx}: {type(exc).__name__}: {exc}")
            cycles_failed += 1
            records_dropped += len(recs)
            continue

        cycles_fetched += 1

        # Find the UH variable. herbie / cfgrib names it 'mxuphl' typically.
        uh_var = None
        for name in ("mxuphl", "MXUPHL", "unknown"):
            if name in ds.data_vars:
                uh_var = name
                break
        if uh_var is None:
            # Fall back: first data variable.
            uh_var = list(ds.data_vars)[0]

        uh_field = np.asarray(ds[uh_var].values).ravel()
        if grid_lats is None:
            grid_lats = np.asarray(ds.latitude.values).ravel()
            grid_lons = np.asarray(ds.longitude.values).ravel()
            # HRRR longitudes are 0..360; convert to -180..180 to match dynametrix.
            grid_lons = np.where(grid_lons > 180.0, grid_lons - 360.0, grid_lons)

        if uh_field.shape != grid_lats.shape:
            print(f"      WARN: UH field shape {uh_field.shape} != grid shape "
                  f"{grid_lats.shape} for init={init_time} fxx={fxx}; skipping cycle")
            cycles_failed += 1
            records_dropped += len(recs)
            continue

        for rec in recs:
            loc_id = rec["location_id"]
            if loc_id not in location_masks:
                lat0 = rec["latitude"]
                lon0 = rec["longitude"]
                # Cheap bounding-box prefilter (1 degree ~= 111 km lat, less in lon).
                # Use a 60 km bbox to be safe around the 40 km circle.
                degree_buffer = 60.0 / 111.0
                bbox_mask = (
                    (np.abs(grid_lats - lat0) < degree_buffer) &
                    (np.abs(grid_lons - lon0) < degree_buffer / max(0.1, math.cos(math.radians(lat0))))
                )
                bbox_idx = np.where(bbox_mask)[0]
                if bbox_idx.size == 0:
                    location_masks[loc_id] = np.array([], dtype=np.int64)
                else:
                    distances = vectorized_haversine(
                        lat0, lon0, grid_lats[bbox_idx], grid_lons[bbox_idx]
                    )
                    in_circle = distances <= UH_NEIGHBORHOOD_KM
                    location_masks[loc_id] = bbox_idx[in_circle]

            neighborhood_idx = location_masks[loc_id]
            if neighborhood_idx.size == 0:
                # Location is outside HRRR coverage (e.g., offshore or out of CONUS).
                records_dropped += 1
                continue

            uh_neighborhood = uh_field[neighborhood_idx]
            n_cells = uh_neighborhood.size
            n_above = int((uh_neighborhood >= UH_THRESHOLD_M2_S2).sum())
            f = n_above / n_cells
            p_hrrr = 1.0 - math.exp(-3.0 * f)

            rec_out = dict(rec)
            rec_out["p_hrrr"] = float(p_hrrr)
            augmented.append(rec_out)

    print(f"      HRRR cycles: {cycles_fetched:,} fetched, {cycles_failed:,} failed.")
    print(f"      Records augmented: {len(augmented):,}; dropped: {records_dropped:,}.")
    return augmented


def match_with_verification(records: List[dict]) -> List[MatchedRecord]:
    """
    Join records with SPC storm-report verification outcomes using the
    existing `verification_engine.find_matching_events` function.

    For each record:
        - Open a DB session.
        - Query ground_truth_events within VERIFICATION_RADIUS_KM (100 km
          per protocol §3.3) of the record's (latitude, longitude), with
          event_at in [issue_time, valid_time].
        - event = 1 if any match found, else 0.
        - event_category = the event_type of the spatially-closest match
          (storm_reports.py populates this with one of 'tornado', 'hail',
          'wind'), else 'none'.

    The result preserves the per-record ordering of `records`. Records
    without a `p_hrrr` field (which would only happen if stub #2 silently
    dropped them) are rejected loudly so the downstream pearson_correlation
    cannot proceed on partially-populated data.
    """
    from app.db.session import SessionLocal
    from app.services.verification_engine import find_matching_events

    valid_categories = {"tornado", "hail", "wind"}
    matched: List[MatchedRecord] = []

    with SessionLocal() as db:
        for rec in records:
            if "p_hrrr" not in rec:
                raise ValueError(
                    f"Record for location_id={rec.get('location_id')} at "
                    f"issue_time={rec.get('issue_time')} is missing p_hrrr; "
                    "load_hrrr_uh_probabilities() must run before "
                    "match_with_verification()."
                )

            events = find_matching_events(
                db,
                latitude=rec["latitude"],
                longitude=rec["longitude"],
                radius_km=VERIFICATION_RADIUS_KM,
                window_start=rec["issue_time"],
                window_end=rec["valid_time"],
            )

            if events:
                # find_matching_events returns events sorted by distance ascending;
                # the closest match drives the category.
                closest_event, _distance_km = events[0]
                raw_category = (closest_event.event_type or "").strip().lower()
                event_category = (
                    raw_category if raw_category in valid_categories else "none"
                )
                event_flag = 1
            else:
                event_category = "none"
                event_flag = 0

            matched.append(MatchedRecord(
                location_id=str(rec["location_id"]),
                issue_time=rec["issue_time"],
                valid_time=rec["valid_time"],
                p_dynametrix=float(rec["p_dynametrix"]),
                p_hrrr=float(rec["p_hrrr"]),
                event=event_flag,
                event_category=event_category,
            ))

    return matched


# =========================================================================
# Diagnostic computation (pure functions, no external dependencies)
# =========================================================================

def compute_residuals(
    matched: List[MatchedRecord],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Residual error of each predictor:
        r = event - predicted_probability

    Returns (r_dynametrix, r_hrrr) as numpy arrays of length len(matched).
    """
    events = np.array([r.event for r in matched], dtype=float)
    p_dyn = np.array([r.p_dynametrix for r in matched], dtype=float)
    p_hrrr = np.array([r.p_hrrr for r in matched], dtype=float)
    return events - p_dyn, events - p_hrrr


def pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation coefficient computed directly (no scipy dep)."""
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    num = float((x_centered * y_centered).sum())
    den = float(np.sqrt((x_centered ** 2).sum() * (y_centered ** 2).sum()))
    return num / den if den > 0 else 0.0


def bootstrap_correlation_ci(
    r_dyn: np.ndarray,
    r_hrrr: np.ndarray,
    events: np.ndarray,
    B: int = BOOTSTRAP_B,
    seed: int = BOOTSTRAP_SEED,
) -> Tuple[float, float, float]:
    """
    Stratified bootstrap (by event / non-event) of Pearson correlation,
    with 95% percentile confidence interval.

    Returns (point_estimate, ci_lower, ci_upper).
    """
    rng = np.random.default_rng(seed)
    point = pearson_correlation(r_dyn, r_hrrr)

    event_idx = np.where(events == 1)[0]
    nonevent_idx = np.where(events == 0)[0]
    n_event = len(event_idx)
    n_nonevent = len(nonevent_idx)

    if n_event == 0 or n_nonevent == 0:
        return point, float('nan'), float('nan')

    boot_corrs = np.empty(B)
    for b in range(B):
        ev_resample = rng.choice(event_idx, size=n_event, replace=True)
        nev_resample = rng.choice(nonevent_idx, size=n_nonevent, replace=True)
        idx = np.concatenate([ev_resample, nev_resample])
        boot_corrs[b] = pearson_correlation(r_dyn[idx], r_hrrr[idx])

    return point, float(np.percentile(boot_corrs, 2.5)), float(np.percentile(boot_corrs, 97.5))


def per_category_breakdown(matched: List[MatchedRecord]) -> dict:
    """
    Per-event-category residual correlation, computed only for categories
    with at least PER_CATEGORY_MIN_EVENTS verified events in the matched
    set. Non-events are pooled across categories for each subset since
    a non-event is a non-event regardless of which category we are
    measuring sensitivity to.

    Returns dict mapping category -> {correlation, sample_size, event_count}.
    """
    result = {}
    nonevents = [r for r in matched if r.event == 0]
    for cat in ('tornado', 'hail', 'wind'):
        cat_events = [r for r in matched if r.event == 1 and r.event_category == cat]
        if len(cat_events) < PER_CATEGORY_MIN_EVENTS:
            continue
        subset = cat_events + nonevents
        r_dyn, r_hrrr = compute_residuals(subset)
        corr = pearson_correlation(r_dyn, r_hrrr)
        result[cat] = {
            'correlation': corr,
            'sample_size': len(subset),
            'event_count': len(cat_events),
        }
    return result


# =========================================================================
# Decision rule (protocol §5; PRE-COMMITTED, do not modify post-result)
# =========================================================================

def decision_from_correlation(point_estimate: float) -> Tuple[str, str]:
    """
    Apply the pre-committed decision rule. Returns (verdict, explanation).
    """
    if point_estimate < THRESHOLD_LOW:
        verdict = "PROCEED"
        explanation = (
            f"Residual correlation {point_estimate:.3f} < {THRESHOLD_LOW} threshold. "
            "Combination has structural room to add value. Proceed with the full "
            "pre-registration under normal AEPF discipline."
        )
    elif point_estimate <= THRESHOLD_HIGH:
        verdict = "PROCEED_WITH_DISCLOSURE"
        explanation = (
            f"Residual correlation {point_estimate:.3f} is in "
            f"[{THRESHOLD_LOW}, {THRESHOLD_HIGH}]. Proceed with the full "
            "pre-registration, BUT add a required disclosure in §9 explicitly "
            "noting the bounded independence and the structurally-constrained "
            "upper bound on combination value."
        )
    else:
        verdict = "DO_NOT_PROCEED"
        explanation = (
            f"Residual correlation {point_estimate:.3f} > {THRESHOLD_HIGH} threshold. "
            "Do not proceed with the full pre-registration. Document the diagnostic "
            "result, archive the draft pre-registration as a 'considered but deferred' "
            "artifact, and direct the next AEPF audit at a different target."
        )
    return verdict, explanation


# =========================================================================
# Output writer
# =========================================================================

def write_diagnostic_summary(
    matched: List[MatchedRecord],
    correlation_result: Tuple[float, float, float],
    per_category: dict,
    transformation_note: str,
    window_start: date,
    window_end: date,
    output_path: Path,
    caveats_md: str = "",
) -> None:
    """Write the diagnostic deliverable per protocol §6.

    If caveats_md is non-empty, it is inserted as a "Sample size and scope
    caveats" section immediately before the decision section, so any
    constraints the operator has surfaced about the data window are visible
    on the same page as the verdict.
    """
    point, ci_lo, ci_hi = correlation_result
    verdict, explanation = decision_from_correlation(point)
    n_total = len(matched)
    n_events = sum(r.event for r in matched)
    mean_r_dyn = float(np.mean([r.event - r.p_dynametrix for r in matched]))
    mean_r_hrrr = float(np.mean([r.event - r.p_hrrr for r in matched]))

    today = date.today().isoformat()

    lines = []
    lines.append("# Diagnostic: Dynametrix v3 vs HRRR Residual Independence")
    lines.append("")
    lines.append("**Status:** EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.")
    lines.append("")
    lines.append(f"**Date:** {today}")
    lines.append(f"**Operator:** Earl Dixon")
    lines.append(f"**Protocol:** INDEPENDENCE_DIAGNOSTIC_PROTOCOL.md")
    lines.append("")
    lines.append("## Data window")
    lines.append(f"- Window: {window_start} through {window_end}")
    lines.append(f"- Matched location-hours: {n_total:,}")
    lines.append(f"- Verified events in matched set: {n_events:,}")
    lines.append("")
    lines.append("## Provisional HRRR-to-probability transformation")
    lines.append(transformation_note)
    lines.append("")
    lines.append("## Primary metric")
    lines.append("")
    lines.append(f"**Pearson correlation of residuals (Dynametrix v3 vs HRRR):** {point:.4f}")
    lines.append(f"**95% bootstrap CI:** [{ci_lo:.4f}, {ci_hi:.4f}]")
    lines.append(f"**Bootstrap:** B = {BOOTSTRAP_B}, seed = 0x{BOOTSTRAP_SEED:X}, "
                 "stratified by event/non-event.")
    lines.append("")
    lines.append("## Sanity checks (mean residuals; near zero = marginally well-calibrated)")
    lines.append(f"- Mean Dynametrix residual: {mean_r_dyn:+.4f}")
    lines.append(f"- Mean HRRR residual: {mean_r_hrrr:+.4f}")
    lines.append("")
    lines.append("## Per-category breakdown")
    if per_category:
        for cat, data in per_category.items():
            lines.append(
                f"- **{cat}**: r = {data['correlation']:.4f}, "
                f"n = {data['sample_size']:,}, events = {data['event_count']:,}"
            )
    else:
        lines.append(f"Insufficient per-category sample sizes "
                     f"(< {PER_CATEGORY_MIN_EVENTS} events per category).")
    lines.append("")
    if caveats_md.strip():
        lines.append("## Sample size and scope caveats")
        lines.append("")
        lines.append(caveats_md.strip())
        lines.append("")
    lines.append("## Decision per protocol §5")
    lines.append("")
    lines.append(f"**Verdict:** {verdict}")
    lines.append("")
    lines.append(explanation)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. Cannot be cited as confirmatory")
    lines.append("evidence in any subsequent published audit. If the finding turns out to be")
    lines.append("substantively interesting in its own right, it must be re-derived under")
    lines.append("proper AEPF lock discipline before publication.*")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote diagnostic summary to {output_path}")


# =========================================================================
# Entrypoint
# =========================================================================

def _validate_window(window_start: date, window_end: date) -> None:
    """Enforce the protocol §2 requirement that the diagnostic window
    does not overlap the prospective evaluation window."""
    if window_start > window_end:
        raise ValueError(f"window_start {window_start} > window_end {window_end}")
    overlaps = not (window_end < EVALUATION_WINDOW_START or
                    window_start > EVALUATION_WINDOW_END)
    if overlaps:
        raise ValueError(
            f"Diagnostic window [{window_start}, {window_end}] overlaps the "
            f"prospective evaluation window [{EVALUATION_WINDOW_START}, "
            f"{EVALUATION_WINDOW_END}]. Per protocol §2, the diagnostic must "
            "use past data only, with no overlap with the future evaluation window."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window-start', type=date.fromisoformat, required=True,
                        help='Diagnostic window start (YYYY-MM-DD).')
    parser.add_argument('--window-end', type=date.fromisoformat, required=True,
                        help='Diagnostic window end (YYYY-MM-DD).')
    parser.add_argument('--transformation-note', type=str, default=(
        f'Updraft helicity (HRRR MXUPHL, 2-5 km AGL) track density above '
        f'{UH_THRESHOLD_M2_S2} m²/s² threshold, integrated over '
        f'{UH_NEIGHBORHOOD_KM} km neighborhood radius, normalized to '
        'probability via SPC HREF-style reference curve.'
    ))
    parser.add_argument('--output', type=Path, required=True,
                        help='Path to write the diagnostic summary markdown.')
    parser.add_argument('--caveats-md', type=Path, default=None,
                        help='Optional path to a markdown file whose contents are '
                             'inserted as a "Sample size and scope caveats" section '
                             'immediately before the decision section.')
    args = parser.parse_args()

    caveats_md = ""
    if args.caveats_md is not None:
        caveats_md = args.caveats_md.read_text(encoding="utf-8")

    _validate_window(args.window_start, args.window_end)

    print(f"[1/5] Loading Dynametrix v3 outputs for "
          f"{args.window_start} to {args.window_end}...")
    raw_records = load_dynametrix_v3_outputs(args.window_start, args.window_end)
    print(f"      Loaded {len(raw_records):,} Dynametrix records.")

    print(f"[2/5] Computing HRRR probabilities for {len(raw_records):,} records...")
    hrrr_records = load_hrrr_uh_probabilities(raw_records)
    print(f"      Augmented {len(hrrr_records):,} records with HRRR probabilities.")

    print("[3/5] Matching with verification outcomes...")
    matched = match_with_verification(hrrr_records)
    print(f"      Matched {len(matched):,} location-hours; "
          f"{sum(r.event for r in matched):,} verified events.")

    if len(matched) < MIN_LOCATION_HOURS:
        print(f"\nINSUFFICIENT DATA: only {len(matched)} matched location-hours; "
              f"need >= {MIN_LOCATION_HOURS}.")
        print("Diagnostic is inconclusive. Defer until more data accumulates.")
        return 1

    print(f"[4/5] Computing bootstrap correlation (B={BOOTSTRAP_B})...")
    r_dyn, r_hrrr = compute_residuals(matched)
    events = np.array([r.event for r in matched], dtype=float)
    correlation_result = bootstrap_correlation_ci(r_dyn, r_hrrr, events)
    point, ci_lo, ci_hi = correlation_result
    print(f"      r = {point:.4f}, 95% CI = [{ci_lo:.4f}, {ci_hi:.4f}]")

    print("[5/5] Per-category breakdown + summary write...")
    per_category = per_category_breakdown(matched)
    write_diagnostic_summary(
        matched=matched,
        correlation_result=correlation_result,
        per_category=per_category,
        transformation_note=args.transformation_note,
        window_start=args.window_start,
        window_end=args.window_end,
        output_path=args.output,
        caveats_md=caveats_md,
    )

    verdict, _ = decision_from_correlation(point)
    print(f"\n=== DIAGNOSTIC VERDICT: {verdict} ===")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
