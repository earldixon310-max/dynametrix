"""
Unblind the sealed key, verify its SHA, compute rank R, and classify outcome
per PRE_REGISTRATION_GW_v1.md Section 6.2.

Usage:
    python unblind_and_rank.py <path_to_sealed_key_csv>

Example:
    python unblind_and_rank.py C:\\Users\\earld\\sealed_keys\\sealed_key_GW_v1.csv
"""

import csv
import hashlib
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCORES_PATH = SCRIPT_DIR / "scores.csv"
COMMITTED_SHA_PATH = SCRIPT_DIR / "sealed_key_sha256.txt"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    sealed_key_path = Path(sys.argv[1])
    if not sealed_key_path.exists():
        print(f"ERROR: sealed key not found at {sealed_key_path}")
        sys.exit(1)
    if not SCORES_PATH.exists():
        print(f"ERROR: scores.csv not found at {SCORES_PATH}")
        sys.exit(1)
    if not COMMITTED_SHA_PATH.exists():
        print(f"ERROR: {COMMITTED_SHA_PATH} not found")
        sys.exit(1)

    print("=" * 72)
    print("SpinPhase GW150914 Blind Test - Unblinding and Rank Computation")
    print("=" * 72)
    print()

    # --- Step 1: SHA verification --------------------------------------
    print("Step 1/4: Verifying sealed key SHA-256 against committed value...")
    committed_sha = COMMITTED_SHA_PATH.read_text().strip().lower()
    actual_sha = hashlib.sha256(sealed_key_path.read_bytes()).hexdigest().lower()
    print(f"  Committed: {committed_sha}")
    print(f"  Actual:    {actual_sha}")
    if actual_sha != committed_sha:
        print("  *** SHA MISMATCH ***")
        print("  The sealed key has been modified since the commit at 5082a58.")
        print("  Test integrity is compromised. Aborting.")
        sys.exit(1)
    print("  MATCH. Sealed key has not been modified since commit.")
    print()

    # --- Step 2: Load and join data ------------------------------------
    print("Step 2/4: Loading sealed key and scores...")
    with open(sealed_key_path, encoding="utf-8") as f:
        sealed = list(csv.DictReader(f))
    with open(SCORES_PATH, encoding="utf-8") as f:
        scores = list(csv.DictReader(f))

    sealed_by_id = {row["blinded_segment_id"]: row for row in sealed}
    print(f"  Loaded {len(sealed)} sealed-key rows, {len(scores)} score rows.")
    print()

    # --- Step 3: Identify event segment --------------------------------
    print("Step 3/4: Identifying GW150914 segment via sealed key...")
    event_blinded_id = None
    for row in sealed:
        if row["segment_type"] == "event_GW150914":
            event_blinded_id = row["blinded_segment_id"]
            break
    if event_blinded_id is None:
        print("ERROR: No row in sealed key has segment_type=event_GW150914.")
        sys.exit(1)
    print(f"  GW150914 blinded_id: {event_blinded_id}")
    print()

    # --- Step 4: Sort by Z, compute rank, classify ---------------------
    print("Step 4/4: Sorting by Z descending and computing rank R...")
    valid_scores = [
        (row["blinded_segment_id"], float(row["Z"]),
         float(row["M_obs"]), float(row["mu_null"]),
         float(row["sigma_null"]), float(row["best_dt_s"]))
        for row in scores
        if row["Z"] != ""
    ]
    valid_scores.sort(key=lambda x: x[1], reverse=True)
    n_valid = len(valid_scores)
    print(f"  Sorted {n_valid} valid scores by Z descending.")

    R = None
    event_row = None
    for i, row in enumerate(valid_scores, start=1):
        if row[0] == event_blinded_id:
            R = i
            event_row = row
            break
    if R is None:
        print("ERROR: GW150914 segment not found among valid scores.")
        sys.exit(1)
    print()

    # --- Outcome classification ----------------------------------------
    if R == 1:
        outcome = "STRONG CLAIM (R = 1)"
        interpretation = (
            "SpinPhase ranks the event-bearing segment above all 99 noise controls. "
            "Suggests SpinPhase has GW150914-morphology detection capability under this protocol."
        )
    elif 2 <= R <= 5:
        outcome = f"INTERESTING (R = {R})"
        interpretation = (
            "SpinPhase places the event in the top 5%. "
            "Worth follow-up but not a strong detection claim."
        )
    elif 6 <= R <= 10:
        outcome = f"SUGGESTIVE (R = {R})"
        interpretation = (
            "Not a detection claim, but the event ranks in the top 10%. "
            "Documented and reported; methodology revision considered."
        )
    else:
        outcome = f"NO DETECTION CAPABILITY UNDER THIS TEST (R = {R})"
        interpretation = (
            "SpinPhase does not, in this protocol, distinguish the GW150914 segment "
            "from background. v1 result remains historical; v2 may be designed if a "
            "clear methodological flaw is identified."
        )

    print("=" * 72)
    print("OUTCOME PER PRE-REGISTRATION SECTION 6.2")
    print("=" * 72)
    print()
    print(f"  GW150914 segment rank R: {R} of {n_valid}")
    print(f"  GW150914 segment Z:      {event_row[1]:+.4f}")
    print(f"  GW150914 segment M_obs:  {event_row[2]:.4f}")
    print(f"  GW150914 segment mu_null:{event_row[3]:.4f}")
    print(f"  GW150914 segment sigma:  {event_row[4]:.4f}")
    print(f"  GW150914 segment best_dt:{event_row[5]:+.4f} s")
    print()
    print(f"  Outcome: {outcome}")
    print(f"    {interpretation}")
    print()

    # --- Top-10 Z values for context -----------------------------------
    print("Top 10 segments by Z descending:")
    print(f"  {'rank':>4}  {'blinded_id':<10}  {'Z':>8}  {'M_obs':>7}  "
          f"{'mu_null':>8}  {'sigma_null':>10}  is_event")
    for i, row in enumerate(valid_scores[:10], start=1):
        marker = "<--- GW150914" if row[0] == event_blinded_id else ""
        print(f"  {i:>4}  {row[0][:8]}..  {row[1]:+.4f}  {row[2]:.4f}  "
              f"{row[3]:.4f}  {row[4]:.4f}      {marker}")
    print()


if __name__ == "__main__":
    main()