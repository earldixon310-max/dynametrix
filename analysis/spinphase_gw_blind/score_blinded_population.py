"""
Score the 100 blinded segments using the frozen SpinPhase pipeline.

Pre-registration: docs/PRE_REGISTRATION_GW_v1.md (Sections 4 and 10)

Reads:  analysis/spinphase_gw_blind/segments_blinded.csv
Writes: analysis/spinphase_gw_blind/scores.csv

Per Section 10.3 of the pre-registration:
  * The score vector must be committed to git BEFORE unblinding.
  * No scores may be modified after the sealed key is revealed.

Usage:
    python score_blinded_population.py
"""

import csv
import sys
import time
from pathlib import Path

from gwpy.timeseries import TimeSeries

from spinphase_pipeline import (
    SAMPLE_RATE_HZ,
    SEGMENT_DURATION_S,
    score_segment,
)


SCRIPT_DIR = Path(__file__).resolve().parent
BLINDED_IN = SCRIPT_DIR / "segments_blinded.csv"
SCORES_OUT = SCRIPT_DIR / "scores.csv"


SCORES_FIELDS = [
    "blinded_segment_id",
    "h1_start_gps",
    "l1_start_gps",
    "M_obs",
    "mu_null",
    "sigma_null",
    "best_dt_s",
    "Z",
    "n_chirp_samples",
    "error",
]


def fetch_strain(detector, gps_start):
    return TimeSeries.fetch_open_data(
        detector, gps_start, gps_start + SEGMENT_DURATION_S,
        sample_rate=SAMPLE_RATE_HZ,
        cache=True, verbose=False,
    )


def main():
    if not BLINDED_IN.exists():
        print(f"ERROR: {BLINDED_IN} not found.")
        sys.exit(1)

    if SCORES_OUT.exists():
        print(f"ERROR: {SCORES_OUT} already exists.")
        print("Refusing to overwrite. The score vector is locked once recorded;")
        print("if you really need to re-score, move the existing file first.")
        sys.exit(1)

    with open(BLINDED_IN, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print("=" * 72)
    print("SpinPhase GW150914 Blind Test - Score Blinded Population")
    print("Pre-registration: docs/PRE_REGISTRATION_GW_v1.md")
    print("=" * 72)
    print()
    print(f"Loaded {len(rows)} blinded segments from {BLINDED_IN.name}.")
    print("Scoring with frozen SpinPhase pipeline...")
    print()

    results = []
    t_start = time.time()

    for i, row in enumerate(rows, start=1):
        bid = row["blinded_segment_id"]
        h1_start = float(row["h1_start_gps"])
        l1_start = float(row["l1_start_gps"])
        prefix = f"[{i:>3}/{len(rows)}] {bid[:8]}... gps={h1_start:.1f}"

        try:
            h1 = fetch_strain("H1", h1_start)
            l1 = fetch_strain("L1", l1_start)
        except Exception as e:
            print(f"{prefix}  FETCH ERROR: {type(e).__name__}: {e}")
            results.append({
                "blinded_segment_id": bid,
                "h1_start_gps": h1_start,
                "l1_start_gps": l1_start,
                "M_obs": "",
                "mu_null": "",
                "sigma_null": "",
                "best_dt_s": "",
                "Z": "",
                "n_chirp_samples": "",
                "error": f"fetch_error:{type(e).__name__}:{e}",
            })
            continue

        try:
            r = score_segment(h1, l1)
        except Exception as e:
            print(f"{prefix}  SCORE ERROR: {type(e).__name__}: {e}")
            results.append({
                "blinded_segment_id": bid,
                "h1_start_gps": h1_start,
                "l1_start_gps": l1_start,
                "M_obs": "",
                "mu_null": "",
                "sigma_null": "",
                "best_dt_s": "",
                "Z": "",
                "n_chirp_samples": "",
                "error": f"score_error:{type(e).__name__}:{e}",
            })
            continue

        print(f"{prefix}  M={r['M_obs']:.4f}  mu={r['mu_null']:.4f}  "
              f"sig={r['sigma_null']:.4f}  Z={r['Z']:+.3f}  "
              f"N={r['n_chirp_samples']}")
        results.append({
            "blinded_segment_id": bid,
            "h1_start_gps": h1_start,
            "l1_start_gps": l1_start,
            "M_obs": f"{r['M_obs']:.6f}",
            "mu_null": f"{r['mu_null']:.6f}",
            "sigma_null": f"{r['sigma_null']:.6f}",
            "best_dt_s": f"{r['best_dt_s']:.6f}",
            "Z": f"{r['Z']:.6f}",
            "n_chirp_samples": r["n_chirp_samples"],
            "error": "",
        })

    t_end = time.time()
    elapsed_min = (t_end - t_start) / 60.0

    print()
    print(f"Writing scores to {SCORES_OUT.name}...")
    with open(SCORES_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCORES_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    n_scored = sum(1 for r in results if r["Z"] != "")
    n_errors = len(results) - n_scored
    print(f"Wrote {len(results)} rows ({n_scored} scored, {n_errors} errors).")
    print(f"Elapsed: {elapsed_min:.1f} minutes.")
    print()
    print("=" * 72)
    print("SCORING COMPLETE")
    print("=" * 72)
    print()
    print("CRITICAL NEXT STEPS:")
    print()
    print(f"  1. Review {SCORES_OUT.name}: {len(rows)} rows expected, error column")
    print("     should be empty for all (or near all) rows.")
    print()
    print(f"  2. Commit scores.csv to git BEFORE unblinding:")
    print(f"        git add analysis/spinphase_gw_blind/{SCORES_OUT.name}")
    print('        git commit -m "GW blind test: lock 100 Z-scores (still blinded)"')
    print()
    print("  3. ONLY AFTER the score commit, reveal the sealed key from")
    print("     C:\\Users\\earld\\sealed_keys\\sealed_key_GW_v1.csv to compute rank R")
    print("     and classify the outcome per Section 6.2.")


if __name__ == "__main__":
    main()