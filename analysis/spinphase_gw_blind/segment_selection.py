"""
SpinPhase GW150914 Blind Test - Segment Selection

Pre-registration: docs/PRE_REGISTRATION_GW_v1.md (locked under commit 24e7ff1)

Modes:
  --dry-run : Validate the environment by fetching ONLY the GW150914 segment
              and computing the reference PSD values. Writes nothing.
              Run this first to confirm gwpy and LIGO open-data access work.

  --full    : Execute the full 100-segment selection per Section 3 of the
              pre-registration. Writes segments_blinded.csv, sealed_key.csv,
              and sealed_key_sha256.txt.
              Requires seed.txt (a single integer) to exist in the same
              directory. The seed must be committed to git BEFORE running --full.

Usage:
    python segment_selection.py --dry-run
    python segment_selection.py --full
"""

import argparse
import csv
import hashlib
import random
import sys
import uuid
from pathlib import Path

import numpy as np


# --- Pre-registered configuration (Sections 3 and 4.1) ---------------------

GW150914_GPS = 1126259462.4          # Published event time (Section 3.2)
SEGMENT_DURATION_S = 32              # Segment length (Section 3.2)
SAMPLE_RATE_HZ = 4096                # Strain sample rate (Section 3.1)

PSD_FFT_LENGTH_S = 4                 # Welch window length (Section 4.1)
PSD_OVERLAP_S = 2                    # 50% overlap (Section 4.1)
PSD_BAND_LOW_HZ = 30                 # Reference band low (Section 3.3)
PSD_BAND_HIGH_HZ = 250               # Reference band high (Section 3.3)
PSD_TOLERANCE = 0.50                 # +/- 50% acceptance band (Section 3.3)

EVENT_SEPARATION_S = 3600            # +/- 1 hour around known events (Section 3.3)
SEGMENT_SEPARATION_S = 64            # Minimum gap between accepted backgrounds
N_BACKGROUND = 99                    # 99 background + 1 event = 100 total
MAX_ATTEMPTS = 10000                 # Safety cap on rejection-sampling loop


# --- O1 observing run bounds and known events ------------------------------

O1_START_GPS = 1126051217            # 2015-09-12 00:00:00 UTC
O1_END_GPS = 1137254417              # 2016-01-19 16:00:00 UTC

KNOWN_O1_EVENTS = {
    "GW150914": 1126259462.4,
    "GW151012": 1128678900.4,        # also catalogued as LVT151012
    "GW151226": 1135136350.6,
}


# --- Output paths (relative to this script) --------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SEED_FILE = SCRIPT_DIR / "seed.txt"
BLINDED_OUT = SCRIPT_DIR / "segments_blinded.csv"
SEALED_KEY_OUT = SCRIPT_DIR / "sealed_key.csv"
SEALED_KEY_SHA = SCRIPT_DIR / "sealed_key_sha256.txt"


# --- Helpers ----------------------------------------------------------------

def _gw150914_segment_window():
    """Return (gps_start, gps_end) for the 32-second segment centered on GW150914."""
    half = SEGMENT_DURATION_S / 2
    return (GW150914_GPS - half, GW150914_GPS + half)


def _fetch_strain(detector, gps_start, duration_s, verbose=True):
    """Fetch open strain data for one detector segment. Returns a gwpy TimeSeries."""
    from gwpy.timeseries import TimeSeries
    gps_end = gps_start + duration_s
    if verbose:
        print(f"  Fetching {detector} strain [{gps_start}, {gps_end})...")
    return TimeSeries.fetch_open_data(
        detector, gps_start, gps_end,
        sample_rate=SAMPLE_RATE_HZ,
        cache=True, verbose=False,
    )


def _mean_psd_in_band(strain_ts):
    """Compute Welch PSD per Section 4.1 and return mean in the [30, 250) Hz band."""
    psd = strain_ts.psd(
        fftlength=PSD_FFT_LENGTH_S,
        overlap=PSD_OVERLAP_S,
        window="hann",
    )
    freqs = psd.frequencies.value
    psd_values = psd.value
    band_mask = (freqs >= PSD_BAND_LOW_HZ) & (freqs < PSD_BAND_HIGH_HZ)
    return float(np.mean(psd_values[band_mask]))


def _load_seed():
    """Load the integer seed from seed.txt. Errors out if missing or malformed."""
    if not SEED_FILE.exists():
        print(f"ERROR: {SEED_FILE.name} not found in {SCRIPT_DIR}.")
        print("Create it with a single integer (e.g. `echo 150914 > seed.txt`)")
        print("and commit it to git BEFORE running --full.")
        sys.exit(1)
    seed_str = SEED_FILE.read_text().strip()
    try:
        return int(seed_str)
    except ValueError:
        print(f"ERROR: seed.txt must contain a single integer, got {seed_str!r}.")
        sys.exit(1)


def _compute_eligible_segments():
    """Build the SegmentList of GPS intervals eligible for background sampling.

    Eligibility = H1_DATA.active intersected with L1_DATA.active,
                  minus +/- 1 hour windows around each known O1 event.

    Implementation note (per Pre-Registration Section 13 addendum):
    The pre-registration Section 3.3 specifies science-quality data with
    CBC CAT1/CAT2/CAT3 vetoes excluded. In GWOSC's open-data API, the
    H1_CBC_CAT1/2/3 flags' active intervals correspond to CATEGORY
    COVERAGE OVER THE ENTIRE OBSERVING RUN, not discrete veto segments;
    subtracting them from H1_DATA zeros the eligible pool entirely.

    For O1 open data, H1_DATA.active represents the publicly released,
    CAT1-cleaned science data segments (CBC veto cleaning is applied
    before public release). Using H1_DATA.active is therefore the
    operational implementation of the pre-reg's science-quality
    requirement within the available API surface. This does not alter
    the population definition or scoring criteria.

    Returns a gwpy SegmentList.
    """
    from gwpy.segments import DataQualityFlag, Segment, SegmentList

    print(f"  Fetching O1 data-quality flags [{O1_START_GPS}, {O1_END_GPS})...")
    print("  (this can take 1-3 minutes)")

    def _fetch_active(detector):
        data_flag = DataQualityFlag.fetch_open_data(
            f"{detector}_DATA", O1_START_GPS, O1_END_GPS
        )
        active = SegmentList(data_flag.active)
        active.coalesce()
        active_s = sum(seg[1] - seg[0] for seg in active)
        print(f"    {detector}_DATA active: {active_s/3600:.1f} hours")
        return active

    h1_active = _fetch_active("H1")
    l1_active = _fetch_active("L1")

    if not h1_active or not l1_active:
        print("ERROR: One or both detectors have zero active time. Aborting.")
        sys.exit(1)

    eligible = h1_active & l1_active
    eligible.coalesce()
    overlap_s = sum(seg[1] - seg[0] for seg in eligible)
    print(f"  H1 and L1 overlap: {overlap_s/3600:.1f} hours")

    print("  Subtracting +/- 1 hour windows around known events...")
    for name, gps in KNOWN_O1_EVENTS.items():
        excl = SegmentList([Segment(gps - EVENT_SEPARATION_S,
                                    gps + EVENT_SEPARATION_S)])
        eligible = eligible - excl
        eligible.coalesce()
        print(f"    after {name} exclusion: "
              f"{sum(s[1]-s[0] for s in eligible)/3600:.1f} hours")

    return eligible


def _sample_gps_in_segments(segments, rng, min_duration):
    """Sample a single GPS time uniformly distributed across `segments`,
    such that [gps, gps + min_duration] fits entirely within one segment.

    Returns the sampled GPS time (float), or None if no segment is long enough.
    """
    valid = [s for s in segments if (s[1] - s[0]) >= min_duration]
    if not valid:
        return None
    durations = [(s[1] - s[0] - min_duration) for s in valid]
    total = sum(durations)
    u = rng.uniform(0.0, total)
    cum = 0.0
    for seg, d in zip(valid, durations):
        if cum + d >= u:
            return seg[0] + (u - cum)
        cum += d
    return valid[-1][1] - min_duration


def _generate_blinded_uuids(rng, n):
    """Generate n deterministic UUID-format strings from rng."""
    ids = []
    for _ in range(n):
        b = bytearray(rng.randbytes(16))
        b[6] = (b[6] & 0x0F) | 0x40   # version 4
        b[8] = (b[8] & 0x3F) | 0x80   # variant 1
        ids.append(str(uuid.UUID(bytes=bytes(b))))
    return ids


# --- Dry run ---------------------------------------------------------------

def dry_run():
    """Validate environment by fetching the GW150914 segment and computing reference PSD."""
    print("=" * 72)
    print("SpinPhase GW150914 Blind Test - Segment Selection - DRY RUN")
    print("Pre-registration: docs/PRE_REGISTRATION_GW_v1.md")
    print("=" * 72)
    print()
    print("Goal: validate environment by fetching ONLY the GW150914 segment")
    print("      and computing reference PSD values. No output files written.")
    print()

    try:
        import gwpy
        from gwpy.timeseries import TimeSeries  # noqa: F401
    except ImportError as e:
        print(f"ERROR: gwpy is not installed. {e}")
        print("Install with: pip install gwpy  (or use the conda env)")
        sys.exit(1)
    print(f"gwpy version: {gwpy.__version__}")
    print()

    gps_start, gps_end = _gw150914_segment_window()
    print(f"GW150914 published time:  {GW150914_GPS}")
    print(f"32-second segment window: [{gps_start}, {gps_end})")
    print()

    print("Fetching GW150914 segment strain...")
    try:
        h1 = _fetch_strain("H1", gps_start, SEGMENT_DURATION_S)
        l1 = _fetch_strain("L1", gps_start, SEGMENT_DURATION_S)
    except Exception as e:
        print(f"ERROR: Failed to fetch strain data: {e}")
        sys.exit(1)

    print(f"  H1: {len(h1)} samples, {h1.sample_rate.value} Hz, "
          f"{h1.duration.value} s")
    print(f"  L1: {len(l1)} samples, {l1.sample_rate.value} Hz, "
          f"{l1.duration.value} s")
    print()

    print(f"Computing reference PSDs "
          f"(Welch, Hann, {PSD_FFT_LENGTH_S}s window, "
          f"{int(100*PSD_OVERLAP_S/PSD_FFT_LENGTH_S)}% overlap)...")
    h1_mean = _mean_psd_in_band(h1)
    l1_mean = _mean_psd_in_band(l1)

    print(f"  H1 mean PSD in [{PSD_BAND_LOW_HZ}, {PSD_BAND_HIGH_HZ}) Hz: "
          f"{h1_mean:.3e}")
    print(f"  L1 mean PSD in [{PSD_BAND_LOW_HZ}, {PSD_BAND_HIGH_HZ}) Hz: "
          f"{l1_mean:.3e}")
    print()

    print(f"Acceptance band per pre-reg Section 3.3 (+/-{int(PSD_TOLERANCE*100)}%):")
    print(f"  H1 candidates: mean PSD in "
          f"[{h1_mean*(1-PSD_TOLERANCE):.3e}, {h1_mean*(1+PSD_TOLERANCE):.3e}]")
    print(f"  L1 candidates: mean PSD in "
          f"[{l1_mean*(1-PSD_TOLERANCE):.3e}, {l1_mean*(1+PSD_TOLERANCE):.3e}]")
    print()

    range_ok = (1e-48 < h1_mean < 1e-40) and (1e-48 < l1_mean < 1e-40)
    if range_ok:
        print("Reference PSD values look plausible.")
    else:
        print("WARNING: PSD values are outside the typical O1 range. Check units.")
    print()
    print("Dry run complete. Environment is ready for --full selection.")


# --- Full selection --------------------------------------------------------

def full_selection():
    """Execute the full 100-segment selection per Section 3 of the pre-registration."""

    # Refuse to overwrite existing output files. Regenerating after the blinded
    # artifact has been committed would invalidate the test.
    existing = [p for p in (BLINDED_OUT, SEALED_KEY_OUT, SEALED_KEY_SHA) if p.exists()]
    if existing:
        print("ERROR: One or more output files already exist:")
        for p in existing:
            print(f"  - {p}")
        print()
        print("Refusing to overwrite. If you genuinely intend to regenerate the")
        print("population (which would invalidate any committed blinded artifact),")
        print("move or delete these files first.")
        sys.exit(1)

    seed = _load_seed()

    print("=" * 72)
    print("SpinPhase GW150914 Blind Test - Segment Selection - FULL")
    print("Pre-registration: docs/PRE_REGISTRATION_GW_v1.md")
    print(f"Seed: {seed}  (loaded from {SEED_FILE.name})")
    print("=" * 72)
    print()

    # Two RNGs: one for sampling candidate GPS times, one for shuffling
    # and UUID generation. Both seeded from the same value so the entire
    # selection is deterministic.
    rng_sample = random.Random(seed)
    rng_shuffle = random.Random(seed + 1)
    rng_uuid = random.Random(seed + 2)

    # --- Step 1/5: GW150914 segment + reference PSDs ---
    print("Step 1/5: Fetching GW150914 segment and computing reference PSDs...")
    gw_start, _ = _gw150914_segment_window()
    h1_ref = _fetch_strain("H1", gw_start, SEGMENT_DURATION_S, verbose=False)
    l1_ref = _fetch_strain("L1", gw_start, SEGMENT_DURATION_S, verbose=False)
    h1_ref_mean = _mean_psd_in_band(h1_ref)
    l1_ref_mean = _mean_psd_in_band(l1_ref)
    h1_lo = h1_ref_mean * (1 - PSD_TOLERANCE)
    h1_hi = h1_ref_mean * (1 + PSD_TOLERANCE)
    l1_lo = l1_ref_mean * (1 - PSD_TOLERANCE)
    l1_hi = l1_ref_mean * (1 + PSD_TOLERANCE)
    print(f"  H1 reference: {h1_ref_mean:.3e}   acceptance [{h1_lo:.3e}, {h1_hi:.3e}]")
    print(f"  L1 reference: {l1_ref_mean:.3e}   acceptance [{l1_lo:.3e}, {l1_hi:.3e}]")
    print()

    # --- Step 2/5: Eligible time pool ---
    print("Step 2/5: Computing eligible time intervals...")
    eligible = _compute_eligible_segments()
    eligible_s = sum(s[1] - s[0] for s in eligible)
    print(f"  Total eligible time: {eligible_s/3600:.1f} hours "
          f"({eligible_s:.0f} seconds)")
    print()

    # --- Step 3/5: Reject-sample background candidates ---
    print(f"Step 3/5: Sampling {N_BACKGROUND} background candidates with PSD filter...")
    print("  Each accepted candidate requires fetching H1+L1 strain.")
    print("  Estimated runtime: 45-90 minutes.")
    print()

    accepted = []
    attempts = 0
    rejection_counts = {"too_close": 0, "fetch_err": 0, "nonfinite": 0,
                        "h1_psd": 0, "l1_psd": 0}

    while len(accepted) < N_BACKGROUND and attempts < MAX_ATTEMPTS:
        attempts += 1
        gps = _sample_gps_in_segments(eligible, rng_sample,
                                       min_duration=SEGMENT_DURATION_S)
        if gps is None:
            print("ERROR: Eligible pool has no segment long enough. Aborting.")
            sys.exit(1)

        if any(abs(gps - a) < SEGMENT_SEPARATION_S for a in accepted):
            rejection_counts["too_close"] += 1
            continue

        try:
            h1 = _fetch_strain("H1", gps, SEGMENT_DURATION_S, verbose=False)
            l1 = _fetch_strain("L1", gps, SEGMENT_DURATION_S, verbose=False)
        except Exception as e:
            rejection_counts["fetch_err"] += 1
            print(f"  attempt {attempts}: gps={gps:.1f}  rejected: fetch error ({type(e).__name__})")
            continue

        if not (np.all(np.isfinite(h1.value)) and np.all(np.isfinite(l1.value))):
            rejection_counts["nonfinite"] += 1
            print(f"  attempt {attempts}: gps={gps:.1f}  rejected: non-finite strain values")
            continue

        h1_psd = _mean_psd_in_band(h1)
        if not (h1_lo <= h1_psd <= h1_hi):
            rejection_counts["h1_psd"] += 1
            print(f"  attempt {attempts}: gps={gps:.1f}  rejected: H1 PSD {h1_psd:.3e} "
                  f"outside [{h1_lo:.3e}, {h1_hi:.3e}]")
            continue

        l1_psd = _mean_psd_in_band(l1)
        if not (l1_lo <= l1_psd <= l1_hi):
            rejection_counts["l1_psd"] += 1
            print(f"  attempt {attempts}: gps={gps:.1f}  rejected: L1 PSD {l1_psd:.3e} "
                  f"outside [{l1_lo:.3e}, {l1_hi:.3e}]")
            continue

        accepted.append(gps)
        print(f"  attempt {attempts}: gps={gps:.1f}  ACCEPTED  "
              f"({len(accepted)}/{N_BACKGROUND} backgrounds)")

    if len(accepted) < N_BACKGROUND:
        print(f"\nERROR: Reached MAX_ATTEMPTS={MAX_ATTEMPTS} with only "
              f"{len(accepted)} accepted. Something is wrong with the "
              f"eligibility pool or the PSD criteria.")
        print("  Rejection counts:")
        for k, v in rejection_counts.items():
            print(f"    {k}: {v}")
        sys.exit(1)

    print()
    print(f"  Total attempts: {attempts}")
    print(f"  Acceptance rate: {N_BACKGROUND/attempts*100:.1f}%")
    for k, v in rejection_counts.items():
        print(f"    rejected ({k}): {v}")
    print()

    # --- Step 4/5: Build blinded population ---
    print("Step 4/5: Building blinded population...")
    population = []
    population.append({
        "h1_start_gps": gw_start,
        "l1_start_gps": gw_start,
        "segment_type": "event_GW150914",
        "background_index": "",
    })
    for i, gps in enumerate(accepted):
        population.append({
            "h1_start_gps": gps,
            "l1_start_gps": gps,
            "segment_type": "background",
            "background_index": i,
        })

    indices = list(range(len(population)))
    rng_shuffle.shuffle(indices)
    population = [population[i] for i in indices]

    blinded_ids = _generate_blinded_uuids(rng_uuid, len(population))
    print(f"  Population: 1 event + {N_BACKGROUND} backgrounds, shuffled, UUIDs assigned.")
    print()

    # --- Step 5/5: Write artifacts ---
    print("Step 5/5: Writing output files...")

    with open(BLINDED_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blinded_segment_id", "h1_start_gps", "l1_start_gps"])
        for bid, item in zip(blinded_ids, population):
            w.writerow([bid, f"{item['h1_start_gps']:.6f}",
                        f"{item['l1_start_gps']:.6f}"])
    print(f"  Wrote {BLINDED_OUT.name} ({len(blinded_ids)} rows)")

    with open(SEALED_KEY_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blinded_segment_id", "segment_type", "background_index"])
        for bid, item in zip(blinded_ids, population):
            w.writerow([bid, item["segment_type"], item["background_index"]])
    print(f"  Wrote {SEALED_KEY_OUT.name} ({len(blinded_ids)} rows)")

    sha = hashlib.sha256(SEALED_KEY_OUT.read_bytes()).hexdigest()
    SEALED_KEY_SHA.write_text(sha + "\n", encoding="utf-8")
    print(f"  Wrote {SEALED_KEY_SHA.name}")
    print(f"  SHA-256: {sha}")
    print()

    # --- Final instructions ---
    print("=" * 72)
    print("FULL SELECTION COMPLETE")
    print("=" * 72)
    print()
    print("CRITICAL NEXT STEPS:")
    print()
    print(f"  1. MOVE {SEALED_KEY_OUT.name} OUT OF THIS REPO IMMEDIATELY.")
    print("     Suggested target: a folder like C:\\Users\\earld\\sealed_keys\\")
    print(f"     Do NOT view, open, or inspect {SEALED_KEY_OUT.name} until scoring is complete.")
    print()
    print(f"  2. Confirm {SEALED_KEY_OUT.name} is no longer in the repo:")
    print(f"        Test-Path {SEALED_KEY_OUT}    # should return False")
    print()
    print(f"  3. Commit {BLINDED_OUT.name} and {SEALED_KEY_SHA.name}:")
    print(f"        git add analysis/spinphase_gw_blind/{BLINDED_OUT.name}")
    print(f"        git add analysis/spinphase_gw_blind/{SEALED_KEY_SHA.name}")
    print('        git commit -m "GW blind test: lock 100-segment blinded population"')
    print()


# --- Entry point -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SpinPhase GW150914 segment selection."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run", action="store_true",
        help="Validate environment using only the GW150914 segment.",
    )
    mode.add_argument(
        "--full", action="store_true",
        help="Execute full 100-segment selection (requires seed.txt).",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.full:
        full_selection()


if __name__ == "__main__":
    main()