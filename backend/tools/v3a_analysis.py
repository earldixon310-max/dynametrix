"""v3a verification analysis — score calibrator-v2.0 predictions at 100 km radius.

Implements the methodology locked in docs/PRE_REGISTRATION_v3a.md (commit aff03b3).
Runs in-memory aggregation against existing CalibratedOutput and ground_truth_events
without persisting separate VerificationOutcome rows. Reports POD, FAR, CSI with
Wilson 95% CIs, Brier score, Brier skill score against climatology, and per-location
breakdown.

Run inside the backend container:
    python tools/v3a_analysis.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import CalibratedOutput, Location, ModelVersion
from app.services.verification import summarize, wilson_score_interval
from app.services.verification_engine import find_matching_events


RADIUS_KM_V3A = 100.0
DECISION_THRESHOLD = 0.5
MODEL_VERSION_TARGET = "calibrator-v2.0"
DEFAULT_WINDOW_HOURS = 24.0


def main() -> None:
    db = SessionLocal()
    try:
        mv = db.scalar(
            select(ModelVersion).where(ModelVersion.version == MODEL_VERSION_TARGET)
        )
        if mv is None:
            print(f"ERROR: ModelVersion '{MODEL_VERSION_TARGET}' not found.")
            return

        now_utc = datetime.now(timezone.utc)

        predictions = list(
            db.scalars(
                select(CalibratedOutput).where(
                    CalibratedOutput.model_version_id == mv.id,
                    CalibratedOutput.commitment_probability.is_not(None),
                )
            )
        )

        pairs: list[tuple[float, bool]] = []
        per_location: dict[str, list[tuple[float, bool]]] = {}
        skipped_window_open = 0
        skipped_missing_location = 0

        for pred in predictions:
            lead_hours = pred.expected_lead_hours or DEFAULT_WINDOW_HOURS
            window_start = pred.observed_at
            window_end = pred.observed_at + timedelta(hours=float(lead_hours))

            if window_end > now_utc:
                skipped_window_open += 1
                continue

            loc = db.get(Location, pred.location_id)
            if loc is None or loc.latitude is None or loc.longitude is None:
                skipped_missing_location += 1
                continue

            matches = find_matching_events(
                db,
                latitude=loc.latitude,
                longitude=loc.longitude,
                radius_km=RADIUS_KM_V3A,
                window_start=window_start,
                window_end=window_end,
            )

            observed = len(matches) > 0
            prob = float(pred.commitment_probability)
            pairs.append((prob, observed))

            label = loc.label
            per_location.setdefault(label, []).append((prob, observed))

        summary = summarize(pairs, threshold=DECISION_THRESHOLD, n_bins=10)

        # Brier skill score against a climatology forecast equal to the base rate
        bss_vs_climatology: Optional[float] = None
        if summary["base_rate"] is not None and summary["brier"] is not None:
            br = summary["base_rate"]
            climatology_brier = br * (1 - br)
            if climatology_brier > 0:
                bss_vs_climatology = 1 - summary["brier"] / climatology_brier

        print("=" * 70)
        print(f"v3a verification — calibrator-v2.0 predictions @ {RADIUS_KM_V3A} km radius")
        print("=" * 70)
        print()
        print(f"Predictions examined: {len(predictions)}")
        print(f"Skipped (window still open): {skipped_window_open}")
        print(f"Skipped (missing location): {skipped_missing_location}")
        print(f"Verified sample size: {summary['n']}")
        print()
        print("Contingency table:")
        print(f"  Hits:                {summary['hits']}")
        print(f"  Misses:              {summary['misses']}")
        print(f"  False alarms:        {summary['false_alarms']}")
        print(f"  Correct negatives:   {summary['correct_negatives']}")
        print()
        print("Metrics @ decision threshold 0.5:")
        if summary["pod"] is not None:
            ci = summary["pod_ci"]
            print(f"  POD:  {summary['pod']:.3f}   95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]")
        else:
            print(f"  POD:  None (no events)")
        if summary["far"] is not None:
            ci = summary["far_ci"]
            print(f"  FAR:  {summary['far']:.3f}   95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]")
        else:
            print(f"  FAR:  None (no yes-forecasts)")
        if summary["csi"] is not None:
            ci = summary["csi_ci"]
            print(f"  CSI:  {summary['csi']:.3f}   95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]")
        else:
            print(f"  CSI:  None")
        print()
        print("Probabilistic scores:")
        if summary["brier"] is not None:
            print(f"  Brier:                  {summary['brier']:.4f}")
        if summary["base_rate"] is not None:
            print(f"  Base rate (events):     {summary['base_rate']:.4f}")
            climatology_brier = summary["base_rate"] * (1 - summary["base_rate"])
            print(f"  Climatology Brier:      {climatology_brier:.4f}")
        if bss_vs_climatology is not None:
            print(f"  BSS vs climatology:     {bss_vs_climatology:+.4f}")
            if bss_vs_climatology > 0:
                print(f"    → BETTER than climatology")
            else:
                print(f"    → WORSE than climatology (negative skill)")
        print()
        print("Per-location breakdown:")
        print(f"  {'Location':<20s}  {'n':>5s}  {'hits':>5s}  {'miss':>5s}  {'FA':>5s}  {'CN':>5s}  {'POD':>7s}  {'FAR':>7s}")
        for label in sorted(per_location.keys()):
            loc_pairs = per_location[label]
            ls = summarize(loc_pairs, threshold=DECISION_THRESHOLD)
            pod_str = f"{ls['pod']:.3f}" if ls["pod"] is not None else "  --  "
            far_str = f"{ls['far']:.3f}" if ls["far"] is not None else "  --  "
            print(
                f"  {label:<20s}  {ls['n']:>5d}  {ls['hits']:>5d}  {ls['misses']:>5d}  "
                f"{ls['false_alarms']:>5d}  {ls['correct_negatives']:>5d}  {pod_str:>7s}  {far_str:>7s}"
            )
        print()
        print("Reliability bins (forecast probability → observed frequency):")
        for b in summary["reliability_bins"]:
            if b["n"] == 0:
                continue
            print(
                f"  [{b['bin_lower']:.1f}, {b['bin_upper']:.1f})  "
                f"n={b['n']:>4d}  mean_forecast={b['mean_forecast']:.3f}  "
                f"observed_freq={b['observed_frequency']:.3f}"
            )
        print()
        print("=" * 70)
        print("End of v3a analysis.")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()