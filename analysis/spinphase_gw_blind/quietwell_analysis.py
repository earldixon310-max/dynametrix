"""
SpinPhase GW150914 Quiet-Well Test - Within-Segment Differential Analysis

Pre-registration: docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md

This script is FROZEN. Per pre-reg Section 10.1, the parameters and
algorithm here must not be modified between commit and the recording
of all 100 D values.

Reads:  analysis/spinphase_gw_blind/segments_blinded.csv
Writes: analysis/spinphase_gw_blind/quietwell_scores.csv

Reuses the v1 frozen pipeline (analysis/spinphase_gw_blind/spinphase_pipeline.py
at git commit 335ce7b) for: whitening, STFT, chirp-track index resolution,
and Δt phase-coherence search. The only new logic here is computing the
phase-coherence statistic at multiple anchor positions per segment and
forming the within-segment differential D.

Usage:
    python quietwell_analysis.py
"""

import csv
import sys
import time
from pathlib import Path

import numpy as np
from gwpy.timeseries import TimeSeries

from spinphase_pipeline import (
    SAMPLE_RATE_HZ,
    SEGMENT_DURATION_S,
    NULL_EPSILON,
    whiten_strain,
    compute_stft,
    chirp_track_indices,
    search_dt,
)


# --- Pre-registered parameters (Section 4.1) ---

# Baseline anchor positions in midpoint-relative seconds. These correspond
# to absolute segment times {2, 5, 8, 11, 14, 18, 21, 24, 27, 30} when the
# segment midpoint is at 16 s. Implementation uses midpoint-relative offsets
# so the anchor positions remain valid regardless of gwpy whitening boundary
# crop (which shortens the whitened array by ~1 s on each side).
BASELINE_OFFSETS_FROM_MIDPOINT_S = [-14, -11, -8, -5, -2, 2, 5, 8, 11, 14]


# --- Paths ---

SCRIPT_DIR = Path(__file__).resolve().parent
BLINDED_IN = SCRIPT_DIR / "segments_blinded.csv"
QW_SCORES_OUT = SCRIPT_DIR / "quietwell_scores.csv"


# --- Output schema ---

QW_FIELDS = (
    ["blinded_segment_id", "h1_start_gps", "l1_start_gps", "S_target"]
    + [f"S_baseline_{i+1}" for i in range(len(BASELINE_OFFSETS_FROM_MIDPOINT_S))]
    + ["mean_baseline", "std_baseline", "D_simple", "D", "error"]
)


# --- Helpers ---

def fetch_strain(detector, gps_start):
    return TimeSeries.fetch_open_data(
        detector, gps_start, gps_start + SEGMENT_DURATION_S,
        sample_rate=SAMPLE_RATE_HZ,
        cache=True, verbose=False,
    )


def coherence_at_anchor(stft_h1, stft_l1, freqs, stft_times, anchor_t):
    """Compute the SpinPhase phase-coherence statistic with the chirp track
    anchored at anchor_t. Returns (M_obs, best_dt_s).
    """
    chirp_indices = chirp_track_indices(stft_times, anchor_t)
    return search_dt(stft_h1, stft_l1, freqs, chirp_indices)


def quietwell_score(strain_h1_ts, strain_l1_ts):
    """Compute S at TARGET and all 10 baseline anchors, then form D.

    Returns dict with keys:
        S_target, S_baseline (list of K=10), mean_baseline, std_baseline,
        D_simple, D
    """
    # Section 4.1 (inherited): whiten both detectors
    h1_w = whiten_strain(strain_h1_ts)
    l1_w = whiten_strain(strain_l1_ts)
    h1_array = np.asarray(h1_w.value, dtype=float)
    l1_array = np.asarray(l1_w.value, dtype=float)
    sample_rate = float(h1_w.sample_rate.value)

    midpoint_t = len(h1_array) / sample_rate / 2.0

    # Section 4.2 (inherited): STFT both detectors
    freqs, times, stft_h1 = compute_stft(h1_array, sample_rate)
    _, _, stft_l1 = compute_stft(l1_array, sample_rate)

    # Section 4.2 (new): coherence at TARGET (segment midpoint)
    s_target, _ = coherence_at_anchor(stft_h1, stft_l1, freqs, times, midpoint_t)

    # Section 4.2 (new): coherence at K=10 BASELINE anchors
    s_baseline = []
    for offset in BASELINE_OFFSETS_FROM_MIDPOINT_S:
        anchor_t = midpoint_t + offset
        s_b, _ = coherence_at_anchor(stft_h1, stft_l1, freqs, times, anchor_t)
        s_baseline.append(s_b)
    s_baseline = np.array(s_baseline, dtype=float)

    # Section 4.3: within-segment differential
    mean_b = float(np.mean(s_baseline))
    std_b = float(np.std(s_baseline, ddof=1))
    d_simple = float(s_target - mean_b)
    d_z = float((s_target - mean_b) / (std_b + NULL_EPSILON))

    return {
        "S_target": float(s_target),
        "S_baseline": s_baseline.tolist(),
        "mean_baseline": mean_b,
        "std_baseline": std_b,
        "D_simple": d_simple,
        "D": d_z,
    }


# --- Main loop -------------------------------------------------------------

def _empty_row(bid, h1_start, l1_start, error_msg):
    row = {
        "blinded_segment_id": bid,
        "h1_start_gps": h1_start,
        "l1_start_gps": l1_start,
        "S_target": "",
        "mean_baseline": "",
        "std_baseline": "",
        "D_simple": "",
        "D": "",
        "error": error_msg,
    }
    for i in range(len(BASELINE_OFFSETS_FROM_MIDPOINT_S)):
        row[f"S_baseline_{i+1}"] = ""
    return row


def main():
    if not BLINDED_IN.exists():
        print(f"ERROR: {BLINDED_IN} not found.")
        sys.exit(1)
    if QW_SCORES_OUT.exists():
        print(f"ERROR: {QW_SCORES_OUT} already exists.")
        print("Refusing to overwrite. The score vector is locked once recorded.")
        sys.exit(1)

    with open(BLINDED_IN, "r", encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))

    print("=" * 72)
    print("SpinPhase GW150914 Quiet-Well Test - Within-Segment Differential")
    print("Pre-registration: docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md")
    print("=" * 72)
    print()
    print(f"Loaded {len(rows_in)} segments from {BLINDED_IN.name}.")
    print(f"K = {len(BASELINE_OFFSETS_FROM_MIDPOINT_S)} baseline anchors at midpoint offsets:")
    print(f"  {BASELINE_OFFSETS_FROM_MIDPOINT_S}")
    print()

    results = []
    t_start = time.time()

    for i, row in enumerate(rows_in, start=1):
        bid = row["blinded_segment_id"]
        h1_start = float(row["h1_start_gps"])
        l1_start = float(row["l1_start_gps"])
        prefix = f"[{i:>3}/{len(rows_in)}] {bid[:8]}.. gps={h1_start:.1f}"

        try:
            h1 = fetch_strain("H1", h1_start)
            l1 = fetch_strain("L1", l1_start)
        except Exception as e:
            print(f"{prefix}  FETCH ERROR: {type(e).__name__}: {e}")
            results.append(_empty_row(bid, h1_start, l1_start,
                                       f"fetch_error:{type(e).__name__}:{e}"))
            continue

        try:
            r = quietwell_score(h1, l1)
        except Exception as e:
            print(f"{prefix}  SCORE ERROR: {type(e).__name__}: {e}")
            results.append(_empty_row(bid, h1_start, l1_start,
                                       f"score_error:{type(e).__name__}:{e}"))
            continue

        out = {
            "blinded_segment_id": bid,
            "h1_start_gps": h1_start,
            "l1_start_gps": l1_start,
            "S_target": f"{r['S_target']:.6f}",
            "mean_baseline": f"{r['mean_baseline']:.6f}",
            "std_baseline": f"{r['std_baseline']:.6f}",
            "D_simple": f"{r['D_simple']:+.6f}",
            "D": f"{r['D']:+.6f}",
            "error": "",
        }
        for j, s_b in enumerate(r["S_baseline"]):
            out[f"S_baseline_{j+1}"] = f"{s_b:.6f}"

        print(f"{prefix}  S_t={r['S_target']:.4f}  mu_b={r['mean_baseline']:.4f}  "
              f"sig_b={r['std_baseline']:.4f}  D={r['D']:+.3f}")
        results.append(out)

    elapsed_min = (time.time() - t_start) / 60.0

    print()
    print(f"Writing scores to {QW_SCORES_OUT.name}...")
    with open(QW_SCORES_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QW_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    n_scored = sum(1 for r in results if r["D"] != "")
    n_errors = len(results) - n_scored
    print(f"Wrote {len(results)} rows ({n_scored} scored, {n_errors} errors).")
    print(f"Elapsed: {elapsed_min:.1f} minutes.")
    print()
    print("=" * 72)
    print("QUIET-WELL ANALYSIS COMPLETE")
    print("=" * 72)
    print()
    print("CRITICAL NEXT STEPS:")
    print()
    print(f"  1. Commit {QW_SCORES_OUT.name} BEFORE inspecting rank R_D:")
    print(f"        git add analysis/spinphase_gw_blind/{QW_SCORES_OUT.name}")
    print('        git commit -m "GW quiet-well: lock 100 D values"')
    print()
    print("  2. THEN compute R_D and classify outcome per pre-reg Section 6.2.")
    print("     The GW150914 segment is blinded_id 2cdc1b70-7106-4cd3-bc61-2bcb5576d4ea")
    print("     (per v1 unblinding). R_D = rank of its D value among 100, sorted descending.")


if __name__ == "__main__":
    main()