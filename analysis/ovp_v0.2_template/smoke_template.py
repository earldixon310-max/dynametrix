#!/usr/bin/env python3
"""smoke_template.py - OVP v0.2 reference SMOKE HARNESS skeleton.

H1-EXEMPT (it must run pre-lock), so its safety is B2: a deny-by-default closed-world input
surface. It shares compute_core with the judge (sec 1c) so the judge's compute is exercised
pre-lock on SYNTHETIC data only. Writes NO results-shaped output. This file is in the locked set.

LESSON (surfaced by execution): libraries must be FULLY WARMED before the closed-world block.
numpy uses lazy submodule imports, so the first `np.random.default_rng` opens a .pyc - which the
closed-world audit (correctly) refuses if it happens inside the block. Warm first, then the data
phase performs only array ops and (for a fixture harness) the single pinned fixture read.
"""
import os
import sys

import numpy as np
import numpy.random  # eager import of the lazy submodule

import ovp_guard
import compute_core

SEED = 1234  # pinned: synthetic generation is a pure function of this seed (no wall-clock/urandom)


def synthetic_loader():
    """Generates synthetic (B, y, C) IN-PROCESS from the pinned seed. Never reads the candidate."""
    rng = np.random.default_rng(SEED)
    n = 400
    y = (rng.random(n) < 0.5).astype(int)
    B = rng.random(n)
    C = np.clip(B + 0.3 * (y - 0.5) + 0.1 * rng.standard_normal(n), 0, 1)  # meaningful synthetic
    return B, y, C


def main():
    np.random.default_rng(0)  # WARM all lazy numpy imports before the closed-world data phase
    # The closed-world guard is active only for the data phase. Empty allowlist here because this
    # harness generates in-process and reads NO fixture. A fixture harness passes the pinned hashed
    # fixture path(s): `with ovp_guard.closed_world_io(FIXTURE_PATH):`
    with ovp_guard.closed_world_io():   # deny ALL file opens during the data phase
        B, y, C = synthetic_loader()
    # exercise the SHARED core on synthetic data (smoke-tests the judge's compute path)
    D_synth = compute_core.compute_sealed(B, y, C, seed=0xC0FFEE)
    assert np.isfinite(D_synth), "compute-core returned non-finite on synthetic data"
    sys.stderr.write("[smoke] OK: shared core ran on synthetic data, D_synth=%.4f (no results written)\n" % D_synth)


if __name__ == "__main__":
    main()
