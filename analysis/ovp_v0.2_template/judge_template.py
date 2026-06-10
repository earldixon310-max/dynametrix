#!/usr/bin/env python3
"""judge_template.py - OVP v0.2 reference JUDGE skeleton.

The guard is the FIRST executable action in main(), before any candidate load. The full closure
chain (sec 2.5) is wired here as ONE unit: H1 self-guard + output-exists + input-hash + (the
harness's B2 is in smoke_template.py). A real study copies this, fills the pinned constants and
the sealed-loader, and shares compute_core with its harness.
"""
import os
import sys

import numpy as np

import ovp_guard
import compute_core

# --- constants PINNED in these locked bytes (identity-covered by H1) ----------------------------
LOCK_TAG = "study-x-lock"                 # this study's signed lock tag (name, not OID)
LOCKED_PATH = "judge_template.py"          # this file's repo-relative path
OUT_PATH = "study_x_results.json"
EXPECTED_INPUT_SHA256 = {                  # pinned here, so H1's blob check covers them
    # "inputs/B_y_C.npz": "<sha256>",
}


def sealed_loader():
    """Loads the REAL candidate. Reached ONLY after the guard has verified the lock."""
    # data = np.load("inputs/B_y_C.npz"); return data["B"], data["y"], data["C"]
    raise NotImplementedError("study fills this in")


def main():
    # 1. H1 FIRST — refuse (exit 2) before the sealed quantity can be formed.
    try:
        ovp_guard.assert_locked_or_refuse(LOCK_TAG, LOCKED_PATH, os.path.abspath(__file__))
        ovp_guard.output_exists_or_refuse(OUT_PATH)       # single-execution
        ovp_guard.verify_input_hashes(EXPECTED_INPUT_SHA256)  # right-data
    except ovp_guard.GuardRefusal as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)
    # 2. only now: load the real candidate and run the SHARED core
    B, y, C = sealed_loader()
    D = compute_core.compute_sealed(B, y, C, seed=0xC0FFEE)
    # 3. write results (single-execution; never re-run silently)
    import json
    json.dump({"D_sealed": D}, open(OUT_PATH, "w"))
    sys.stderr.write("[judge] wrote %s\n" % OUT_PATH)


if __name__ == "__main__":
    main()
