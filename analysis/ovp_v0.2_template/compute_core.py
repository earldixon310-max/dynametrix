"""compute_core.py - the SHARED, PURE compute-core (OVP v0.2 template).

Imported by BOTH the judge (sealed-loader) and the smoke harness (synthetic-loader). This is the
resolution to H1's un-smoke-testability (sec 1c): the harness exercises this EXACT code on
synthetic data pre-lock, so a dtype/shape defect cannot first surface at the irreversible run.

PURE: no file/network IO, no global entropy. Deterministic in `seed`. A real study replaces the
body with its HDG/estimator; the contract (pure, seeded, returns the sealed scalar) is fixed.
"""
import numpy as np


def compute_sealed(B, y, C, seed, reps=200):
    """Placeholder sealed computation. Real studies: paired-split median HDG, etc.
    Here: a deterministic, pure function of the inputs + seed (stands in for the real estimator)."""
    rng = np.random.default_rng(seed)
    B = np.asarray(B, float); y = np.asarray(y, float); C = np.asarray(C, float)
    acc = []
    for _ in range(reps):
        idx = rng.permutation(len(B))[: len(B) // 2]
        acc.append(np.corrcoef(C[idx], y[idx])[0, 1] - np.corrcoef(B[idx], y[idx])[0, 1])
    return float(np.median(acc))
