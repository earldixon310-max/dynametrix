#!/usr/bin/env python3
"""judge_template.py - OVP v0.2 reference JUDGE skeleton (rev2).

H1 now covers EVERY sealed-path source (judge + shared core + guard) via SEALED_SOURCES, so an
accidental post-lock edit to the shared core refuses instead of silently corrupting the verdict.
The guard is the FIRST action in main(), before any candidate load.
"""
import os
import sys

import numpy as np

import ovp_guard
import compute_core

# --- constants PINNED in these locked bytes (identity-covered by H1) ----------------------------
LOCK_TAG = "study-x-lock"
LOCKED_PATH = "judge_template.py"           # repo-relative; the dict KEY/lookup path (not __file__)
OUT_PATH = "study_x_results.json"
EXPECTED_INPUT_SHA256 = {                   # pinned here; H1 covers them; empty => refuse (rev2)
    # "inputs/B_y_C.npz": "<sha256>",
}
# EVERY source file reached on the sealed compute path. A lint should assert this covers all
# sealed-path imports. Values are the actually-loaded files (module.__file__), hashed for identity.
SEALED_SOURCES = {
    LOCKED_PATH: os.path.abspath(__file__),
    "compute_core.py": os.path.abspath(compute_core.__file__),
    "ovp_guard.py": os.path.abspath(ovp_guard.__file__),
    # .gitattributes governs the -text filter H1's hash-object --path comparison relies on, so an
    # accidental post-lock edit to it must also refuse (cold-pass-A reader #3). Keys are repo-relative.
    ".gitattributes": os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gitattributes"),
}


def sealed_loader():
    """Loads the REAL candidate. Reached ONLY after the guard verifies the lock."""
    raise NotImplementedError("study fills this in")


def main():
    try:
        ovp_guard.assert_locked_or_refuse(LOCK_TAG, SEALED_SOURCES, os.path.abspath(__file__))
        ovp_guard.output_exists_or_refuse(OUT_PATH)
        ovp_guard.verify_input_hashes(EXPECTED_INPUT_SHA256)   # empty -> refuse (rev2)
    except ovp_guard.GuardRefusal as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)
    B, y, C = sealed_loader()
    D = compute_core.compute_sealed(B, y, C, seed=0xC0FFEE)
    import json
    json.dump({"D_sealed": D}, open(OUT_PATH, "w"))
    sys.stderr.write("[judge] wrote %s\n" % OUT_PATH)


if __name__ == "__main__":
    main()
