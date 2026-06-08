#!/usr/bin/env python3
"""
judge_direction.py - DETECTOR_DIRECTION_OVP candidate study (OVP real candidate #3).
Implements PRE_REGISTRATION_DETECTOR_DIRECTION_OVP.md.

Judges whether `predicted_prob_ai` (the detector's raw DIRECTIONAL probability) adds
Held-out Discriminative Gain beyond the baseline confidence B (= max(p,1-p), folded)
in predicting detector correctness y, against the SAME cut points frozen by
DETECTOR_OVP_CALIB. This third real verdict reaches the §6 operational rung.

  D > TAU_HI            -> Validated
  D < TAU_LO            -> Not-Validated   (mechanism-agnostic in v0.1)
  TAU_LO <= D <= TAU_HI -> Inconclusive
where D = median(HDG_AUC over R=200 stratified 50/50 PAIRED splits), no trimming.

Everything (B, y, predicted_prob_ai, pred) is INHERITED + hash-verified from the
calibration-locked detector_per_example.csv. NO materialization, tokenizer, or model run.

NO-PEEKING (heightened): the directional marginal (accuracy-by-predicted-class) is close
to the HDG and is NOT computed pre-lock. --seed/--reps are determinism plumbing, NOT a
smoke; running this script always computes p's real HDG. The Section 8 smoke is a separate
synthetic harness (B,y only). Single-execution under seed 0xDEC0DE. verify_cut_points()
aborts on inheritance drift.
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

MASTER_SEED = 0xDEC0DE
R = 200
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")

TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
CALIB_RESULT_TAG = "detector-ovp-calib-result"
CALIB_RESULTS_JSON = os.path.join("..", "detector_truncation_ovp", "detector_calibration_results.json")

INHERITED_PER_EXAMPLE = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
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


def verify_cut_points():
    if not os.path.exists(CALIB_RESULTS_JSON):
        raise SystemExit("ABORT: %s not found; cannot verify inherited cut points." % CALIB_RESULTS_JSON)
    cal = json.load(open(CALIB_RESULTS_JSON))
    if not (cal.get("tau_lo") == TAU_LO and cal.get("tau_hi") == TAU_HI):
        raise SystemExit("ABORT: hardcoded cut points (%r, %r) != calibration result (%r, %r); drift."
                         % (TAU_LO, TAU_HI, cal.get("tau_lo"), cal.get("tau_hi")))


def load_inherited():
    actual = sha256_file(INHERITED_PER_EXAMPLE)
    if actual != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s; inherited substrate is not the "
                         "calibration-locked one." % (INHERITED_PER_EXAMPLE, actual, EXPECTED_PER_EXAMPLE_SHA256))
    df = pd.read_csv(INHERITED_PER_EXAMPLE)
    return df, actual


def estimator():
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))


def hdg_paired(B, C, y, rng):
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

    D = float(np.median(d_auc))
    if D > TAU_HI:
        verdict = "Validated"
    elif D < TAU_LO:
        verdict = "Not-Validated"
    else:
        verdict = "Inconclusive"

    return {
        "D_median_HDG_AUC": D, "verdict": verdict,
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
    ap.add_argument("--out", default="detector_direction_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - NOT the locked run; STILL computes "
              "predicted_prob_ai's real HDG (NOT a no-peeking smoke).")
    if args.reps != R:
        print("[WARN] non-canonical reps %d (canonical R=%d) - NOT the locked run; STILL computes the "
              "real HDG (NOT a smoke)." % (args.reps, R))

    verify_cut_points()
    print("[1/2] inheriting (B, y, predicted_prob_ai, pred) from the calibration lock (hash-verified) ...")
    df, per_example_hash = load_inherited()
    print("      verified %s sha256=%s" % (INHERITED_PER_EXAMPLE, per_example_hash))
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    C = df["predicted_prob_ai"].to_numpy().astype(float)
    pred = df["pred"].to_numpy().astype(int)
    print("      n=%d accuracy=%.3f n_errors=%d" % (len(B), y.mean(), int((y == 0).sum())))

    print("[2/2] judging `predicted_prob_ai` against the inherited band over %d paired splits ..." % args.reps)
    res = judge(B, C, y, args.seed, args.reps)
    # non-gating per-predicted-class diagnostics (computed once in the locked run; pre-reg sec 7/9)
    res["support_nongating"]["n_examples"] = int(len(B))
    res["support_nongating"]["n_errors"] = int((y == 0).sum())
    res["support_nongating"]["accuracy_given_pred1"] = float(y[pred == 1].mean()) if (pred == 1).any() else None
    res["support_nongating"]["accuracy_given_pred0"] = float(y[pred == 0].mean()) if (pred == 0).any() else None
    res["support_nongating"]["n_pred1"] = int((pred == 1).sum())
    res["support_nongating"]["n_pred0"] = int((pred == 0).sum())
    res["meta"] = {"candidate": "predicted_prob_ai", "baseline": "confidence (folded max(p,1-p))",
                   "master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_canonical": R, "reps_used": args.reps,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "dataset_sha256": DATASET_SHA256,
                   "inherited_per_example_sha256": per_example_hash,
                   "estimator": ESTIMATOR_DESC,
                   "cut_points_provenance": CALIB_RESULT_TAG,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ["D_median_HDG_AUC", "verdict", "tau_lo", "tau_hi", "band_relation"]}, indent=2))


if __name__ == "__main__":
    main()
