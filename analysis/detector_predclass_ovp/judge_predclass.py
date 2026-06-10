#!/usr/bin/env python3
"""
judge_predclass.py - DETECTOR_PREDCLASS_OVP candidate study (OVP real candidate #4).
Implements PRE_REGISTRATION_DETECTOR_PREDCLASS_OVP.md. First study under the OVP v0.2
Descriptor Justification Layer (mechanism disclosure + dual interpretation + surface foil).

Judges whether `pred` (binary predicted class) adds Held-out Discriminative Gain beyond
folded confidence B = max(p,1-p) in predicting detector correctness y, against the SAME
cut points frozen by DETECTOR_OVP_CALIB.

  D > TAU_HI            -> Validated
  D < TAU_LO            -> Not-Validated   (mechanism-agnostic in v0.1)
  TAU_LO <= D <= TAU_HI -> Inconclusive
where D = median(HDG_AUC over R=200 stratified 50/50 PAIRED splits), no trimming.

PERMUTED-PRED FOIL (non-gating): on the SAME split as the real candidate (shared baseline),
[B, pred_perm] HDG is computed with pred permuted via an INDEPENDENT deterministic stream
SeedSequence(MASTER ^ 0xF011). 200 foil values, persisted; D_foil = median. Expected below
TAU_LO: pred_perm is target-independent, so it cannot lift held-out AUC in expectation -- the
foil doubles as a band-validity / methodology check. The foil NEVER enters pred's verdict; if
it clears TAU_LO the result carries the §6 RED-FLAG caveat (methodological artifact, NOT
legitimate marginal structure; suspend interpretive trust pending investigation).

Everything (B, y, pred) is INHERITED + hash-verified; NO materialization/tokenizer/model run.
NO-PEEKING (heightened): the per-class marginal is the DISCLOSED mechanism (public from #3);
the HDG-beyond-confidence is the sealed verdict, computed only by this single locked run.
Single-execution under seed 0xC1A55D. verify_cut_points() aborts on inheritance drift.
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

MASTER_SEED = 0xC1A55D
FOIL_SEED_XOR = 0xF011
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
    return pd.read_csv(INHERITED_PER_EXAMPLE), actual


def estimator():
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))


def fitp(Xtr, ytr, Xte):
    return estimator().fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def verdict_of(D):
    if D > TAU_HI:
        return "Validated"
    if D < TAU_LO:
        return "Not-Validated"
    return "Inconclusive"


def judge(B, y, pred, master_seed, reps):
    children = np.random.SeedSequence(master_seed).spawn(reps)
    foil_children = np.random.SeedSequence(master_seed ^ FOIL_SEED_XOR).spawn(reps)
    n = len(B)
    X1 = B.reshape(-1, 1)
    d_auc = np.empty(reps)
    d_ap = np.empty(reps)
    foil_auc = np.empty(reps)
    for r in range(reps):
        rng = np.random.default_rng(children[r])
        ss = int(rng.integers(0, 2**31 - 1))
        idx_tr, idx_te = train_test_split(np.arange(n), test_size=0.5, stratify=y, random_state=ss)
        ytr, yte = y[idx_tr], y[idx_te]
        # baseline (shared by real candidate and foil on this split)
        p1 = fitp(X1[idx_tr], ytr, X1[idx_te])
        auc1 = roc_auc_score(yte, p1)
        ap1 = average_precision_score(1 - yte, 1 - p1)
        # real candidate [B, pred]
        X2 = np.column_stack([B, pred])
        p2 = fitp(X2[idx_tr], ytr, X2[idx_te])
        d_auc[r] = roc_auc_score(yte, p2) - auc1
        d_ap[r] = average_precision_score(1 - yte, 1 - p2) - ap1
        # FOIL [B, pred_perm], independent permutation stream, SAME split
        frng = np.random.default_rng(foil_children[r])
        pred_perm = pred.copy()
        frng.shuffle(pred_perm)
        X2f = np.column_stack([B, pred_perm])
        p2f = fitp(X2f[idx_tr], ytr, X2f[idx_te])
        foil_auc[r] = roc_auc_score(yte, p2f) - auc1

    D = float(np.median(d_auc))
    D_foil = float(np.median(foil_auc))
    return {
        "D_median_HDG_AUC": D, "verdict": verdict_of(D),
        "tau_lo": TAU_LO, "tau_hi": TAU_HI,
        "band_relation": {"D_gt_tau_hi": bool(D > TAU_HI), "D_lt_tau_lo": bool(D < TAU_LO),
                          "D_in_band": bool(TAU_LO <= D <= TAU_HI)},
        "support_nongating": {
            "HDG_AUC_mean": float(np.mean(d_auc)), "HDG_AUC_P5": float(np.percentile(d_auc, 5)),
            "HDG_AUC_P95": float(np.percentile(d_auc, 95)),
            "frac_reps_above_tau_hi": float(np.mean(d_auc > TAU_HI)),
            "frac_reps_below_tau_lo": float(np.mean(d_auc < TAU_LO)),
            "frac_reps_in_band": float(np.mean((d_auc >= TAU_LO) & (d_auc <= TAU_HI))),
            "AP_error_class_median": float(np.median(d_ap)),
            # --- permuted-pred FOIL (non-gating; pre-reg sec 4/6) ---
            "foil_D_median": D_foil,
            "foil_verdict": verdict_of(D_foil),
            "foil_HDG_mean": float(np.mean(foil_auc)), "foil_HDG_P5": float(np.percentile(foil_auc, 5)),
            "foil_HDG_P95": float(np.percentile(foil_auc, 95)),
            # all three band fractions, symmetric with the real candidate's (audit parity)
            "foil_frac_above_tau_hi": float(np.mean(foil_auc > TAU_HI)),
            "foil_frac_below_tau_lo": float(np.mean(foil_auc < TAU_LO)),
            "foil_frac_in_band": float(np.mean((foil_auc >= TAU_LO) & (foil_auc <= TAU_HI))),
            "foil_pre_commitment_met": bool(D_foil < TAU_LO),   # expected: foil lands below tau_lo
            "foil_clears_tau_lo": bool(D_foil >= TAU_LO),       # if True -> §6 RED-FLAG caveat (methodology artifact; suspend interpretive trust)
        },
        "hdg_distribution": {"AUC": d_auc.tolist(), "AP_error_class": d_ap.tolist(),
                             "foil_AUC": foil_auc.tolist()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED)
    ap.add_argument("--reps", type=int, default=R)
    ap.add_argument("--out", default="detector_predclass_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - NOT the locked run; STILL computes "
              "pred's real HDG (NOT a no-peeking smoke).")
    if args.reps != R:
        print("[WARN] non-canonical reps %d (canonical R=%d) - NOT the locked run; STILL computes the "
              "real HDG (NOT a smoke)." % (args.reps, R))

    verify_cut_points()
    print("[1/2] inheriting (B, y, pred) from the calibration lock (hash-verified) ...")
    df, per_example_hash = load_inherited()
    print("      verified %s sha256=%s" % (INHERITED_PER_EXAMPLE, per_example_hash))
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    pred = df["pred"].to_numpy().astype(float)
    print("      n=%d accuracy=%.3f n_errors=%d" % (len(B), y.mean(), int((y == 0).sum())))

    print("[2/2] judging `pred` (+ permuted-pred foil) against the inherited band over %d paired splits ..." % args.reps)
    res = judge(B, y, pred, args.seed, args.reps)
    predi = pred.astype(int)
    res["support_nongating"]["n_examples"] = int(len(B))
    res["support_nongating"]["n_errors"] = int((y == 0).sum())
    res["support_nongating"]["accuracy_given_pred1"] = float(y[predi == 1].mean()) if (predi == 1).any() else None
    res["support_nongating"]["accuracy_given_pred0"] = float(y[predi == 0].mean()) if (predi == 0).any() else None
    res["support_nongating"]["n_pred1"] = int((predi == 1).sum())
    res["support_nongating"]["n_pred0"] = int((predi == 0).sum())
    res["meta"] = {"candidate": "pred", "baseline": "confidence (folded max(p,1-p))",
                   "master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "foil_seed_xor": hex(FOIL_SEED_XOR),
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
    print("foil (non-gating): D_foil=%.6f verdict=%s pre_commitment_met=%s" %
          (res["support_nongating"]["foil_D_median"], res["support_nongating"]["foil_verdict"],
           res["support_nongating"]["foil_pre_commitment_met"]))


if __name__ == "__main__":
    main()
