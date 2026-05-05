"""
Compute rank R_D for the GW150914 segment in quietwell_scores.csv and
classify the outcome per PRE_REGISTRATION_GW_QUIETWELL_v1.md Section 6.2.

The GW150914 blinded_id was revealed during v1 unblinding; it is the same
across both tests since both use the same locked blinded population.

Usage:
    python rank_quietwell.py
"""

import csv
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
QW_SCORES = SCRIPT_DIR / "quietwell_scores.csv"
GW150914_BLINDED_ID = "2cdc1b70-7106-4cd3-bc61-2bcb5576d4ea"


def main():
    if not QW_SCORES.exists():
        print(f"ERROR: {QW_SCORES} not found.")
        sys.exit(1)

    with open(QW_SCORES, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print("=" * 72)
    print("SpinPhase GW150914 Quiet-Well - Rank and Outcome Classification")
    print("=" * 72)
    print()

    valid = [
        (r["blinded_segment_id"], float(r["D"]),
         float(r["S_target"]), float(r["mean_baseline"]),
         float(r["std_baseline"]), float(r["D_simple"]))
        for r in rows if r["D"] != ""
    ]
    valid.sort(key=lambda x: x[1], reverse=True)
    n_valid = len(valid)
    print(f"Sorted {n_valid} valid D values descending.")
    print()

    R_D = None
    event_row = None
    for i, row in enumerate(valid, start=1):
        if row[0] == GW150914_BLINDED_ID:
            R_D = i
            event_row = row
            break
    if R_D is None:
        print(f"ERROR: GW150914 blinded_id {GW150914_BLINDED_ID} not found.")
        sys.exit(1)

    if R_D == 1:
        outcome = "STRONG CLAIM (R_D = 1)"
        interp = ("Within-segment elevation at the GW150914 anchor exceeds "
                  "the same statistic at every other segment's anchor.")
    elif 2 <= R_D <= 5:
        outcome = f"INTERESTING (R_D = {R_D})"
        interp = ("GW150914 within-segment differential is in the top 5%. "
                  "Worth follow-up testing on additional GW events.")
    elif 6 <= R_D <= 10:
        outcome = f"SUGGESTIVE (R_D = {R_D})"
        interp = "Top 10%. Documented and reported."
    else:
        outcome = f"NO LOCAL EMERGENCE UNDER THIS TEST (R_D = {R_D})"
        interp = ("SpinPhase's coherence statistic does not register a "
                  "within-segment elevation at the GW150914 event location "
                  "any more than at random target windows in random segments.")

    print("=" * 72)
    print("OUTCOME PER PRE-REG SECTION 6.2")
    print("=" * 72)
    print()
    print(f"  GW150914 rank R_D:        {R_D} of {n_valid}")
    print(f"  GW150914 D (z-score):     {event_row[1]:+.4f}")
    print(f"  GW150914 D_simple:        {event_row[5]:+.4f}")
    print(f"  GW150914 S_target:        {event_row[2]:.4f}")
    print(f"  GW150914 mean(S_baseline):{event_row[3]:.4f}")
    print(f"  GW150914 std(S_baseline): {event_row[4]:.4f}")
    print()
    print(f"  Outcome: {outcome}")
    print(f"    {interp}")
    print()

    print("Top 10 segments by D descending:")
    print(f"  {'rank':>4}  {'blinded_id':<10}  {'D':>8}  {'S_target':>8}  "
          f"{'mu_b':>7}  {'sig_b':>7}  is_event")
    for i, row in enumerate(valid[:10], start=1):
        marker = "<--- GW150914" if row[0] == GW150914_BLINDED_ID else ""
        print(f"  {i:>4}  {row[0][:8]}..  {row[1]:+.4f}  {row[2]:.4f}  "
              f"{row[3]:.4f}  {row[4]:.4f}    {marker}")
    print()


if __name__ == "__main__":
    main()