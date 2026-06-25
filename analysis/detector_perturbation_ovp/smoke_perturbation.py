#!/usr/bin/env python3
"""smoke_perturbation.py - synthetic smoke for DETECTOR_PERTURBATION_OVP (OVP #5).

H1-EXEMPT (runs pre-lock); safety is B2 closed-world IO for the data phase. Shares compute_core
with the judge, so the judge's EXACT compute path (estimator + foil + confound + flip-rate) is
exercised pre-lock on SYNTHETIC data only. Writes NO results-shaped output. Never reads the candidate.

Asserts the four pre-committed smoke properties:
  (1) known-meaningful C        -> Validated
  (2) known-null C              -> Not-Validated
  (3) the meaningful run's permuted-C foil lands below tau_lo (foil_pre_commitment_met)
  (4) a length-proxy C collapses under [B, length] -> confound_genuine == False  (and a genuine C -> True)

Runs on a machine with sklearn (the locked estimator); the sandbox lacks it.
"""
import os
import sys

import numpy as np
import numpy.random  # eager import of the lazy submodule

import ovp_guard
import compute_core

SEED = 1234
TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
EPS = 0.005
REPS = 60   # smoke reps (non-locked); the locked run uses R=200


def _scenarios():
    rng = np.random.default_rng(SEED)
    n = 400
    out = {}
    # (A) meaningful: C strongly predicts y beyond an independent B; Z independent of (y, C)
    y = (rng.random(n) < 0.5).astype(int)
    B = 0.5 + 0.15 * rng.standard_normal(n)
    C = 1.5 * (y - 0.5) + 0.25 * rng.standard_normal(n)
    Z = np.column_stack([rng.standard_normal(n), (rng.random(n) < 0.5).astype(float)])  # length, domain
    out["meaningful"] = (B, y, C, np.zeros(n), Z)
    # (B) null: C independent of y
    y2 = (rng.random(n) < 0.5).astype(int)
    B2 = 0.5 + 0.15 * rng.standard_normal(n)
    C2 = rng.standard_normal(n)
    Z2 = np.column_stack([rng.standard_normal(n), (rng.random(n) < 0.5).astype(float)])
    out["null"] = (B2, y2, C2, np.zeros(n), Z2)
    # (C) length-proxy confound: length predicts y; C = length + noise; B independent
    length = rng.standard_normal(n)
    y3 = (rng.random(n) < 1 / (1 + np.exp(-1.6 * length))).astype(int)
    B3 = 0.5 + 0.15 * rng.standard_normal(n)
    C3 = length + 0.25 * rng.standard_normal(n)
    Z3 = np.column_stack([length, (rng.random(n) < 0.5).astype(float)])
    out["confound"] = (B3, y3, C3, np.zeros(n), Z3)
    return out


def main():
    # WARM numpy + sklearn lazy imports before the closed-world data phase
    np.random.default_rng(0)
    _ = compute_core._fitp(np.zeros((4, 1)), np.array([0, 1, 0, 1]), np.zeros((2, 1)))

    with ovp_guard.closed_world_io():     # deny ALL file opens during synthetic data generation
        scen = _scenarios()

    res_m = compute_core.compute_sealed(*scen["meaningful"], TAU_LO, TAU_HI, EPS, SEED, REPS)
    res_n = compute_core.compute_sealed(*scen["null"], TAU_LO, TAU_HI, EPS, SEED, REPS)
    res_c = compute_core.compute_sealed(*scen["confound"], TAU_LO, TAU_HI, EPS, SEED, REPS)

    assert res_m["verdict"] == "Validated", "(1) meaningful C should Validate, got %s (D=%.4f)" % (res_m["verdict"], res_m["D_median_HDG_AUC"])
    assert res_n["verdict"] == "Not-Validated", "(2) null C should Not-Validate, got %s (D=%.4f)" % (res_n["verdict"], res_n["D_median_HDG_AUC"])
    assert res_m["support_nongating"]["foil_pre_commitment_met"], "(3) meaningful run's permuted foil should land below tau_lo"
    assert res_c["support_nongating"]["confound_genuine"] is False, "(4) length-proxy C should collapse under [B,length] (confound caveat)"
    assert res_m["support_nongating"]["confound_genuine"] is True, "(4b) genuine C should survive the confound covariates"

    sys.stderr.write("[smoke] OK: (1) meaningful Validated D=%.4f | (2) null Not-Validated D=%.4f | "
                     "(3) foil_met=%s D_foil=%.4f | (4) length-proxy confound_genuine=%s gap=%.4f | "
                     "(4b) genuine confound_genuine=%s\n" % (
                         res_m["D_median_HDG_AUC"], res_n["D_median_HDG_AUC"],
                         res_m["support_nongating"]["foil_pre_commitment_met"], res_m["support_nongating"]["foil_D_median"],
                         res_c["support_nongating"]["confound_genuine"], res_c["support_nongating"]["confound_gap"],
                         res_m["support_nongating"]["confound_genuine"]))


if __name__ == "__main__":
    main()
