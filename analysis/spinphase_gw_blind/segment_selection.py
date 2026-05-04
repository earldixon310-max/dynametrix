"""
SpinPhase GW150914 Blind Test - Segment Selection

Pre-registration: docs/PRE_REGISTRATION_GW_v1.md (locked under commit 24e7ff1)

Modes:
  --dry-run : Validate the environment by fetching ONLY the GW150914 segment
              and computing the reference PSD values. Writes nothing.
              Run this first to confirm gwpy and LIGO open-data access work.

  --full    : Execute the full 100-segment selection per Section 3 of the
              pre-registration. Writes segments_blinded.csv, sealed_key.csv,
              and sealed_key_sha256.txt. NOT YET IMPLEMENTED.

Usage:
    python segment_selection.py --dry-run
    python segment_selection.py --full
"""

import argparse
import sys
from pathlib import Path

import numpy as np


# --- Configuration (matches pre-registration Sections 3 and 4.1) -----------

GW150914_GPS = 1126259462.4          # Published event time (Section 3.2)
SEGMENT_DURATION_S = 32              # Segment length (Section 3.2)
SAMPLE_RATE_HZ = 4096                # Strain sample rate (Section 3.1)

PSD_FFT_LENGTH_S = 4                 # Welch window length (Section 4.1)
PSD_OVERLAP_S = 2                    # 50% overlap (Section 4.1)
PSD_BAND_LOW_HZ = 30                 # Reference band low (Section 3.3)
PSD_BAND_HIGH_HZ = 250               # Reference band high (Section 3.3)
PSD_TOLERANCE = 0.50                 # ±50% acceptance band (Section 3.3)


# --- Helpers ----------------------------------------------------------------

def _gw150914_segment_window():
    """Return (gps_start, gps_end) for the 32-second segment centered on GW150914."""
    half = SEGMENT_DURATION_S / 2
    return (GW150914_GPS - half, GW150914_GPS + half)


def _fetch_strain(detector, gps_start, duration_s):
    """Fetch open strain data for one detector segment. Returns a gwpy TimeSeries."""
    from gwpy.timeseries import TimeSeries
    gps_end = gps_start + duration_s
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
        print("Install with: pip install gwpy")
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
        print("Check network connection and try again.")
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

    print(f"Acceptance band per pre-reg Section 3.3 (±{int(PSD_TOLERANCE*100)}%):")
    print(f"  H1 candidates: mean PSD in "
          f"[{h1_mean*(1-PSD_TOLERANCE):.3e}, {h1_mean*(1+PSD_TOLERANCE):.3e}]")
    print(f"  L1 candidates: mean PSD in "
          f"[{l1_mean*(1-PSD_TOLERANCE):.3e}, {l1_mean*(1+PSD_TOLERANCE):.3e}]")
    print()

    # Sanity check: typical O1 strain PSD in 30-250 Hz is ~1e-46 to 1e-42 Hz^-1
    range_ok = True
    if not (1e-48 < h1_mean < 1e-40):
        print(f"WARNING: H1 mean PSD ({h1_mean:.3e}) is outside the typical O1 range. "
              "Check units.")
        range_ok = False
    if not (1e-48 < l1_mean < 1e-40):
        print(f"WARNING: L1 mean PSD ({l1_mean:.3e}) is outside the typical O1 range. "
              "Check units.")
        range_ok = False

    if range_ok:
        print("Reference PSD values look plausible.")
    print()
    print("Dry run complete. Environment is ready for --full selection.")


# --- Full selection (placeholder) ------------------------------------------

def full_selection():
    """Execute the full 100-segment selection per Section 3.

    NOT YET IMPLEMENTED. Will be filled in once the dry run is validated.
    """
    print("ERROR: --full selection mode is not yet implemented.")
    print("Run --dry-run first to validate the environment, then we will")
    print("implement the full selection logic in a follow-up commit.")
    sys.exit(1)


# --- Entry point -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SpinPhase GW150914 segment selection."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run", action="store_true",
        help="Validate the environment using only the GW150914 segment.",
    )
    mode.add_argument(
        "--full", action="store_true",
        help="Execute the full 100-segment selection (not yet implemented).",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.full:
        full_selection()


if __name__ == "__main__":
    main()