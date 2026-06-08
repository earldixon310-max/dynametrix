#!/usr/bin/env python3
"""
judge_truncation.py - DETECTOR_TRUNCATION_OVP candidate study (lock 2).
Implements PRE_REGISTRATION_DETECTOR_TRUNCATION_OVP.md.

Judges whether the candidate observable `truncated` adds Held-out Discriminative Gain
(HDG) beyond the baseline (detector confidence B) in predicting detector correctness y,
against the cut points frozen by DETECTOR_OVP_CALIB.

Single real-candidate verdict (spec v0.1 three-verdict structure):
  D > TAU_HI            -> Validated
  D < TAU_LO            -> Not-Validated   (mechanism-agnostic in v0.1)
  TAU_LO <= D <= TAU_HI -> Inconclusive
where D = median(HDG_AUC over R=200 stratified 50/50 paired splits), ordinary median
over ALL 200 replications (no trimming/truncation). Estimator and materialization are
inherited from the calibration (StandardScaler train-fit -> L2 logistic; per-example
B,y,truncated read + hash-verified, no model re-run).

Single-execution: the LOCKED verdict is produced by ONE run under canonical seed 0x77C0DE.
NO-PEEKING WARNING: the --seed/--reps flags are determinism/plumbing only and are NOT a
no-peeking smoke. This script ALWAYS loads `truncated` and computes its real HDG, so running
it with ANY flags still computes the candidate's verdict. The Section 8 build-and-smoke is a
SEPARATE synthetic harness that never loads `truncated`; do not use this script to "smoke".
The script also asserts its hardcoded cut points against the calibration result at runtime
(verify_cut_points), so an inheritance drift aborts rather than silently judging on stale cuts.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---- pinned constants (pre-reg sec 4, 5, 11) ----
MASTER_SEED = 0x77C0DE
R = 200
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")

# ---- inherited cut points (sec 5), verbatim from detector_calibration_results.json ----
TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
CALIB_RESULT_TAG = "detector-ovp-calib-result"
CALIB_RESULTS_JSON = "detector_calibration_results.json"   # the inherited-from result (committed at the calibration lock)

# ---- inherited substrate (sec 2), hash-verified ----
PER_EXAMPLE_CSV = "detector_per_example.csv"
PER_EXAMPLE_HASH_FILE = "detector_per_example_sha256.txt"
EXPECTED_PER_EXAMPLE_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
DATASET_SHA256 = "a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inherited():
    """Read the calibration-locked per-example (B, y, truncated); verify sha256 against
    the pinned anchor AND the recorded hash file. No model re-run (sec 2). Abort on mismatch."""
    actual = sha256_file(PER_EXAMPLE_CSV)
    if actual != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s; inherited substrate is not the "
                         "calibration-locked one." % (PER_EXAMPLE_CSV, actual, EXPECTED_PER_EXAMPLE_SHA256))
    if os.path.exists(PER_EXAMPLE_HASH_FILE):
        recorded = open(PER_EXAMPLE_HASH_FILE).read().strip().split()[0]
        if recorded != actual:
            raise SystemExit("ABORT: %s (%s) disagrees with %s (%s)." %
                             (PER_EXAMPLE_HASH_FILE, recorded, PER_EXAMPLE_CSV, actual))
    df = pd.read_csv(PER_EXAMPLE_CSV)
    return df, actual


def verify_cut_points():
    """Defense-in-depth on the inheritance chain: assert the hardcoded TAU_LO/TAU_HI are
    byte-identical to the calibration result they are inherited from, so a later drift
    (stale copy-paste, accidental edit) aborts rather than silently judging on wrong cuts.
    Requires the calibration result (committed at detector-ovp-calib-result) to be present."""
    if not os.path.exists(CALIB_RESULTS_JSON):
        raise SystemExit("ABORT: %s not found; cannot verify inherited cut points." % CALIB_RESULTS_JSON)
    cal = json.load(open(CALIB_RESULTS_JSON))
    if not (cal.get("tau_lo") == TAU_LO and cal.get("tau_hi") == TAU_HI):
        raise SystemExit("ABORT: hardcoded cut points (%r, %r) != calibration result (%r, %r); "
                         "inheritance drift." % (TAU_LO, TAU_HI, cal.get("tau_lo"), cal.get("tau_hi")))


def estimator():
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))


def hdg_paired(B, C, y, rng):
    """Paired HDG on one stratified 50/50 split: baseline [B] and candidate [B,C] share
    the SAME train/test rows. Returns (d_auc, d_ap_error_class)."""
    X1 = B.reshape(-1, 1)
    X2 = np.column_stack([B, C])
    ss = int(rng.integers(0, 2**31 - 1))
    X1tr, X1te, X2tr, X2te, ytr, yte = train_test_split(
        X1, X2, y, test_size=0.5, stratify=y, random_state=ss
    )
    p1 = estimator().fit(X1tr, ytr).predict_proba(X1te)[:, 1]
    p2 = estimator().fit(X2tr, ytr).predict_proba(X2te)[:, 1]
    d_auc = roc_auc_score(yte, p2) - roc_auc_score(yte, p1)
    d_ap = (average_precision_score(1 - yte, 1 - p2)
            - average_precision_score(1 - yte, 1 - p1))   # error-as-positive
    return d_auc, d_ap


def judge(B, C, y, master_seed, reps):
    children = np.random.SeedSequence(master_seed).spawn(reps)
    d_auc = np.empty(reps)
    d_ap = np.empty(reps)
    for r in range(reps):
        rng = np.random.default_rng(children[r])
        d_auc[r], d_ap[r] = hdg_paired(B, C, y, rng)

    D = float(np.median(d_auc))   # the gating scalar: median over ALL reps, no trimming
    if D > TAU_HI:
        verdict = "Validated"
    elif D < TAU_LO:
        verdict = "Not-Validated"
    else:
        verdict = "Inconclusive"

    return {
        "D_median_HDG_AUC": D,
        "verdict": verdict,
        "tau_lo": TAU_LO, "tau_hi": TAU_HI,
        "band_relation": {"D_gt_tau_hi": bool(D > TAU_HI), "D_lt_tau_lo": bool(D < TAU_LO),
                          "D_in_band": bool(TAU_LO <= D <= TAU_HI)},
        "support_nongating": {
            "HDG_AUC_mean": float(np.mean(d_auc)),
            "HDG_AUC_P5": float(np.percentile(d_auc, 5)),
            "HDG_AUC_P95": float(np.percentile(d_auc, 95)),
            "frac_reps_above_tau_hi": float(np.mean(d_auc > TAU_HI)),
            "frac_reps_below_tau_lo": float(np.mean(d_auc < TAU_LO)),
            "frac_reps_in_band": float(np.mean((d_auc >= TAU_LO) & (d_auc <= TAU_HI))),
            "AP_error_class_median": float(np.median(d_ap)),
        },
        "hdg_distribution": {"AUC": d_auc.tolist(), "AP_error_class": d_ap.tolist()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED)
    ap.add_argument("--reps", type=int, default=R)
    ap.add_argument("--out", default="detector_truncation_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - NOT the locked run; this STILL "
              "computes truncated's real HDG (this is NOT a no-peeking smoke).")
    if args.reps != R:
        print("[WARN] non-canonical reps %d (canonical R=%d) - NOT the locked run; STILL computes "
              "truncated's real HDG (NOT a no-peeking smoke)." % (args.reps, R))

    verify_cut_points()   # abort if the hardcoded cut points have drifted from the calibration result
    print("[1/2] loading inherited per-example (B, y, truncated) from the calibration lock (hash-verified) ...")
    df, per_example_hash = load_inherited()
    print("      verified %s  sha256=%s" % (PER_EXAMPLE_CSV, per_example_hash))
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    C = df["truncated"].to_numpy().astype(float)
    print("      n=%d, accuracy=%.3f, n_errors=%d, truncated_prevalence=%.3f" %
          (len(B), y.mean(), int((y == 0).sum()), C.mean()))

    print("[2/2] judging `truncated` against the inherited band over %d paired splits ..." % args.reps)
    res = judge(B, C, y, args.seed, args.reps)
    res["support_nongating"]["n_examples"] = int(len(B))
    res["support_nongating"]["n_errors"] = int((y == 0).sum())
    res["support_nongating"]["truncated_prevalence"] = float(C.mean())
    res["meta"] = {"candidate": "truncated", "baseline": "confidence (max softmax)",
                   "master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_canonical": R, "reps_used": args.reps,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "dataset_sha256": DATASET_SHA256,
                   "detector_per_example_sha256": per_example_hash,
                   "estimator": ESTIMATOR_DESC,
                   "cut_points_provenance": CALIB_RESULT_TAG,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ["D_median_HDG_AUC", "verdict", "tau_lo", "tau_hi", "band_relation"]}, indent=2))


if __name__ == "__main__":
    main()
