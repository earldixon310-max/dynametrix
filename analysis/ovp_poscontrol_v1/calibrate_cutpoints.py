#!/usr/bin/env python3
"""
calibrate_cutpoints.py - OVP_POSCONTROL_v1 cut-point calibration study.

Implements PRE_REGISTRATION_OVP_POSCONTROL_v1_CALIB.md strictly. This script
SETS the HDG decision cut points (tau_lo, tau_hi) and the two band-relative arm
parameters (Arm 1 sigma_C, Arm 3 sigma3) for OVP_POSCONTROL_v1, by measuring the
HDG distributions of known-null and known-meaningful constructions under the
study's own seed (0xCA11B) - the spec section 1 bootstrap path.

Single-execution: this runs exactly once, after lock, under the canonical seed.
A non-canonical --seed is provided only for pre-lock smoke testing; it must never
be used for the locked run.

Conformance notes (choices pinned in the pre-reg; see SCRIPT_BUILD_FINDINGS_CALIB.md):
  - estimator: sklearn LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000,
    fit_intercept=True), features NOT standardized (raw B, C).
  - percentile method: numpy default 'linear' (type-7).
  - per-replication seeding: one np.random.SeedSequence child per replication
    (index order); within a replication the substrate (s1,s2,y,B) is drawn once
    and shared across all constructions, then each construction's C is drawn in a
    fixed construction order. Faithful to "one child per replication".
  - Arm 3 is NOISE-attenuated (C = B + s2 + Normal(0, sigma3^2)), not scale-
    parameterized: the linear estimator is scale-invariant, so a scaled clean s2
    would not control HDG; only noise attenuates the recoverable signal.
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

# ---- pinned constants (pre-reg sections 3, 4, 5, 12) ----
MASTER_SEED = 0xCA11B
R_CAL = 200
N = 4000
BETA1 = 1.0
BETA2 = 1.0
SIGMA_B = 1.0
DELTA = 0.01                                     # separability / tau_hi clearance margin (AUC)
SIGMA_C_GRID = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]   # meaningful sweep (smaller = stronger)
SIGMA3_GRID = [1.5, 2.0, 3.0, 4.0, 5.0, 6.0]     # partial (Arm-3 form) noise sweep (sigma3)

LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def draw_substrate(rng, n):
    """One substrate draw shared across constructions within a replication."""
    s1 = rng.standard_normal(n)
    s2 = rng.standard_normal(n)
    eps_b = rng.standard_normal(n) * SIGMA_B
    B = s1 + eps_b
    p = sigmoid(BETA1 * s1 + BETA2 * s2)
    y = (rng.random(n) < p).astype(int)
    return s1, s2, B, y


def hdg(B, C, y, rng):
    """D = AUC_test(logistic[B,C]) - AUC_test(logistic[B]) on a stratified 50/50 split."""
    Xb = B.reshape(-1, 1)
    Xf = np.column_stack([B, C])
    split_seed = int(rng.integers(0, 2**31 - 1))
    Xb_tr, Xb_te, Xf_tr, Xf_te, y_tr, y_te = train_test_split(
        Xb, Xf, y, test_size=0.5, stratify=y, random_state=split_seed
    )
    auc_b = roc_auc_score(y_te, LogisticRegression(**LOGIT_KW).fit(Xb_tr, y_tr).predict_proba(Xb_te)[:, 1])
    auc_f = roc_auc_score(y_te, LogisticRegression(**LOGIT_KW).fit(Xf_tr, y_tr).predict_proba(Xf_te)[:, 1])
    return auc_f - auc_b, auc_b


def candidate(kind, param, s1, s2, B, rng, n):
    """Construct C for a given construction. Fixed construction order is enforced by caller."""
    if kind == "null_redundant":
        return 2.0 * B - 0.5
    if kind == "null_noise":
        return rng.standard_normal(n)
    if kind == "meaningful":               # param = sigma_C (observation noise on s2)
        return s2 + rng.standard_normal(n) * param
    if kind == "partial":                  # param = sigma3 (noise level on the s2 increment)
        return B + s2 + rng.standard_normal(n) * param
    raise ValueError(kind)


def key_of(kind, param):
    return kind if param is None else f"{kind}:{param}"


def run(master_seed, reps):
    children = np.random.SeedSequence(master_seed).spawn(reps)
    # constructions in FIXED order (pre-reg section 5); C-noise consumes the rng in this order
    constructions = [("null_redundant", None), ("null_noise", None)]
    constructions += [("meaningful", s) for s in SIGMA_C_GRID]
    constructions += [("partial", s) for s in SIGMA3_GRID]

    hdgs = {key_of(k, p): [] for k, p in constructions}
    auc_b_all = []

    for r in range(reps):
        rng = np.random.default_rng(children[r])
        s1, s2, B, y = draw_substrate(rng, N)
        for k, p in constructions:
            C = candidate(k, p, s1, s2, B, rng, N)
            d, auc_b = hdg(B, C, y, rng)
            hdgs[key_of(k, p)].append(d)
            if k == "null_noise":
                auc_b_all.append(auc_b)

    hdgs = {k: np.array(v) for k, v in hdgs.items()}
    return derive_cutpoints(hdgs, np.array(auc_b_all))


def pctl(a, q):
    return float(np.percentile(a, q))   # numpy default 'linear' (type-7), pinned (F1)


def derive_cutpoints(hdgs, auc_b_all):
    out = {"meta": {"master_seed": hex(MASTER_SEED),
                    "R_cal": len(next(iter(hdgs.values()))),
                    "N": N, "delta": DELTA,
                    "generated": datetime.now(timezone.utc).isoformat()}}

    # tau_lo = max of the two nulls' P95 (pre-reg section 6)
    p95_red = pctl(hdgs["null_redundant"], 95)
    p95_noise = pctl(hdgs["null_noise"], 95)
    tau_lo = max(p95_red, p95_noise)

    # tau_hi + Arm1 sigma_C: weakest (largest sigma_C) meaningful point whose P5 > tau_lo + delta
    tau_hi = None
    arm1_sigma_c = None
    meaningful_p5 = {}
    for s in sorted(SIGMA_C_GRID, reverse=True):     # largest sigma_C (weakest) first
        p5 = pctl(hdgs[f"meaningful:{s}"], 5)
        meaningful_p5[s] = p5
        if tau_hi is None and p5 > tau_lo + DELTA:
            tau_hi = p5
            arm1_sigma_c = s

    # Arm3 sigma3: median HDG closest to band midpoint (tiebreak: smallest sigma3 = strongest)
    arm3_sigma3 = None
    partial_median = {}
    if tau_hi is not None:
        mid = (tau_lo + tau_hi) / 2.0
        best = None
        for s in SIGMA3_GRID:                         # ascending -> smallest sigma3 wins ties
            med = float(np.median(hdgs[f"partial:{s}"]))
            partial_median[s] = med
            dist = abs(med - mid)
            if best is None or dist < best[0]:
                best = (dist, s)
        arm3_sigma3 = best[1]

    # margins (pre-reg section 8): explicit numbers for the spec section 4 "pinned margin"
    arm1_margin = None
    if arm1_sigma_c is not None:
        arm1_median = float(np.median(hdgs[f"meaningful:{arm1_sigma_c}"]))
        arm1_margin = arm1_median - tau_hi
    arm4_margin = tau_lo - float(np.median(hdgs["null_noise"]))

    # separability checks (pre-reg section 7)
    meaningful_means = {s: float(np.mean(hdgs[f"meaningful:{s}"])) for s in SIGMA_C_GRID}
    desc = sorted(SIGMA_C_GRID, reverse=True)
    monotonic = all(meaningful_means[a] <= meaningful_means[b] for a, b in zip(desc, desc[1:]))
    nulls_nonpos = (float(np.mean(hdgs["null_redundant"])) <= 1e-9) and \
                   (float(np.mean(hdgs["null_noise"])) <= 1e-9)
    sigma3_in_band = tau_hi is not None and any(
        tau_lo <= float(np.median(hdgs[f"partial:{s}"])) <= tau_hi for s in SIGMA3_GRID
    )
    checks = {
        "1_tau_lo_positive": bool(tau_lo > 0),
        "2_band_exists": bool(tau_hi is not None and (tau_hi - tau_lo) >= DELTA),
        "3_monotonic_and_nulls_nonpositive": bool(monotonic and nulls_nonpos),
        "4_band_targetable_sigma3": bool(sigma3_in_band),
    }
    separable = all(checks.values())

    out.update({
        "tau_lo": tau_lo,
        "tau_hi": tau_hi,
        "arm1_sigma_C": arm1_sigma_c,
        "arm3_sigma3": arm3_sigma3,
        "arm1_margin_above_tau_hi": arm1_margin,
        "arm4_margin_below_tau_lo": arm4_margin,
        "support": {
            "p95_null_redundant": p95_red,
            "p95_null_noise": p95_noise,
            "meaningful_P5": {str(k): v for k, v in meaningful_p5.items()},
            "meaningful_mean": {str(k): v for k, v in meaningful_means.items()},
            "partial_median": {str(k): v for k, v in partial_median.items()},
            "baseline_auc_median": float(np.median(auc_b_all)),
        },
        "separability_checks": checks,
        "SEPARABLE": separable,
        "verdict": "USABLE BAND" if separable else "MIS-SPECIFIED - revise under new lock",
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED,
                    help="master seed; default is the locked canonical 0xCA11B. "
                         "Use a non-canonical value ONLY for pre-lock smoke testing.")
    ap.add_argument("--reps", type=int, default=R_CAL)
    ap.add_argument("--out", default="calibration_results.json")
    args = ap.parse_args()

    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - smoke test only, NOT the locked run.")

    res = run(args.seed, args.reps)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)

    keys = ["tau_lo", "tau_hi", "arm1_sigma_C", "arm3_sigma3",
            "arm1_margin_above_tau_hi", "arm4_margin_below_tau_lo", "SEPARABLE", "verdict"]
    print(json.dumps({k: res[k] for k in keys}, indent=2))


if __name__ == "__main__":
    main()
