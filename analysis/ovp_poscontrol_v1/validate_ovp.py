#!/usr/bin/env python3
"""
validate_ovp.py - OVP_POSCONTROL_v1 positive control (the self-validation gate).

Implements PRE_REGISTRATION_OVP_POSCONTROL_v1.md. Runs the locked OVP v0.1 decision
rule (HDG vs two frozen cut points -> one of three verdicts) over four synthetic
arms whose correct verdicts are known by construction, R=100 replications under
master seed 0xFACADE, and checks the per-arm pass bars and setup controls.

Cut points and arm parameters are FROZEN from the calibration study result
(tag ovp-poscontrol-v1-calib-result, calibration_results.json). They are hardcoded
here at full precision and cross-checked against that file at startup so they
cannot silently drift.

Single-execution: runs exactly once, after lock, under the canonical seed 0xFACADE.
A non-canonical --seed is for pre-lock smoke testing only; never the locked run.

Instantiation is identical to the calibration study (metric/estimator/split/N);
only the seed (0xFACADE) and R (100) differ. See pre-reg sec 2.
"""
import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

# ---- pinned constants (pre-reg sec 2, 3, 7, 8) ----
MASTER_SEED = 0xFACADE
R = 100
N = 4000
BETA1 = 1.0
BETA2 = 1.0
SIGMA_B = 1.0
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)

# ---- FROZEN from the calibration result (tag ovp-poscontrol-v1-calib-result) ----
TAU_LO = 0.0008520905552347899
TAU_HI = 0.016157622564950937
ARM1_SIGMA_C = 2.0
ARM3_SIGMA3 = 4.0

# ---- pass bars / setup-control thresholds (pre-reg sec 7, 8) ----
GATE = 90                 # gated arms require >= 90 of R correct
NONDEGEN_AUC = 0.60       # setup control 1: median baseline AUC must exceed this
ARMS = ["arm1", "arm2", "arm3", "arm4"]   # fixed construction order


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def draw_substrate(rng, n):
    s1 = rng.standard_normal(n)
    s2 = rng.standard_normal(n)
    B = s1 + rng.standard_normal(n) * SIGMA_B
    y = (rng.random(n) < sigmoid(BETA1 * s1 + BETA2 * s2)).astype(int)
    return s1, s2, B, y


def hdg(B, C, y, rng):
    Xb = B.reshape(-1, 1)
    Xf = np.column_stack([B, C])
    ss = int(rng.integers(0, 2**31 - 1))
    Xb_tr, Xb_te, Xf_tr, Xf_te, y_tr, y_te = train_test_split(
        Xb, Xf, y, test_size=0.5, stratify=y, random_state=ss
    )
    ab = roc_auc_score(y_te, LogisticRegression(**LOGIT_KW).fit(Xb_tr, y_tr).predict_proba(Xb_te)[:, 1])
    af = roc_auc_score(y_te, LogisticRegression(**LOGIT_KW).fit(Xf_tr, y_tr).predict_proba(Xf_te)[:, 1])
    return af - ab, ab


def candidate(arm, s1, s2, B, rng, n):
    if arm == "arm1":   # known-meaningful
        return s2 + rng.standard_normal(n) * ARM1_SIGMA_C
    if arm == "arm2":   # deterministic-redundant
        return 2.0 * B - 0.5
    if arm == "arm3":   # partial-redundancy (noise-attenuated)
        return B + s2 + rng.standard_normal(n) * ARM3_SIGMA3
    if arm == "arm4":   # pure noise
        return rng.standard_normal(n)
    raise ValueError(arm)


def verdict(D):
    if D > TAU_HI:
        return "Validated"
    if D < TAU_LO:
        return "Not-Validated"
    return "Inconclusive"


def run(master_seed, reps):
    children = np.random.SeedSequence(master_seed).spawn(reps)
    tally = {a: {"Validated": 0, "Not-Validated": 0, "Inconclusive": 0} for a in ARMS}
    hsum = {a: [] for a in ARMS}
    auc_b = []
    for r in range(reps):
        rng = np.random.default_rng(children[r])
        s1, s2, B, y = draw_substrate(rng, N)
        for a in ARMS:
            C = candidate(a, s1, s2, B, rng, N)
            D, ab = hdg(B, C, y, rng)
            tally[a][verdict(D)] += 1
            hsum[a].append(D)
            if a == "arm1":
                auc_b.append(ab)   # baseline AUC (B alone); representative for non-degeneracy
    hmean = {a: float(np.mean(hsum[a])) for a in ARMS}
    return evaluate(tally, hmean, float(np.median(auc_b)), reps)


def evaluate(tally, hmean, auc_b_median, reps):
    gated = {
        "arm1_Validated_ge_gate": tally["arm1"]["Validated"] >= GATE,
        "arm2_NotValidated_ge_gate": tally["arm2"]["Not-Validated"] >= GATE,
        "arm4_NotValidated_ge_gate": tally["arm4"]["Not-Validated"] >= GATE,
    }
    setup = {
        "1_nondegeneracy_baseline_auc_gt_0.60": auc_b_median > NONDEGEN_AUC,
        "2_nulls_centered_mean_HDG_le_tau_lo": (hmean["arm2"] <= TAU_LO) and (hmean["arm4"] <= TAU_LO),
        "3_cutpoint_validity_0_lt_lo_lt_hi": (0 < TAU_LO < TAU_HI),
    }
    gated_ok = all(gated.values())
    setup_ok = all(setup.values())
    if not setup_ok:
        overall = "SETUP-CONTROL FAILURE - run invalidated (not a verdict; amend under new tag)"
    elif gated_ok:
        overall = "PASS - OVP reaches the self-validated rung (sec 6.1)"
    else:
        overall = "FAIL / near-miss - reported honestly, no reseed, no softened threshold"
    return {
        "meta": {
            "master_seed": hex(MASTER_SEED), "R": reps, "N": N,
            "tau_lo": TAU_LO, "tau_hi": TAU_HI,
            "arm1_sigma_C": ARM1_SIGMA_C, "arm3_sigma3": ARM3_SIGMA3,
            "gate": GATE, "generated": datetime.now(timezone.utc).isoformat(),
        },
        "per_arm_verdicts": tally,
        "per_arm_mean_HDG": hmean,
        "baseline_auc_median": auc_b_median,
        "gated_bars": gated,
        "arm3_distribution_nongated": tally["arm3"],
        "setup_controls": setup,
        "VERDICT": overall,
    }


def crosscheck_calibration():
    """If calibration_results.json sits next to this script, assert the frozen values match it."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_results.json")
    if not os.path.exists(path):
        print("[note] calibration_results.json not found next to script; using hardcoded frozen values.")
        return
    cal = json.load(open(path))
    for k, v in [("tau_lo", TAU_LO), ("tau_hi", TAU_HI),
                 ("arm1_sigma_C", ARM1_SIGMA_C), ("arm3_sigma3", ARM3_SIGMA3)]:
        assert abs(cal[k] - v) < 1e-12, f"FROZEN {k}={v} does not match calibration_results.json ({cal[k]})"
    print("[ok] frozen cut points match calibration_results.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED,
                    help="master seed; default is the locked canonical 0xFACADE. "
                         "Non-canonical values are for pre-lock smoke testing only.")
    ap.add_argument("--reps", type=int, default=R)
    ap.add_argument("--out", default="poscontrol_results.json")
    args = ap.parse_args()

    crosscheck_calibration()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - smoke test only, NOT the locked run.")

    res = run(args.seed, args.reps)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)

    keys = ["per_arm_verdicts", "gated_bars", "setup_controls", "arm3_distribution_nongated", "VERDICT"]
    print(json.dumps({k: res[k] for k in keys}, indent=2))


if __name__ == "__main__":
    main()
