#!/usr/bin/env python3
"""
judge_length.py - DETECTOR_LENGTH_OVP candidate study (OVP real candidate #2).
Implements PRE_REGISTRATION_DETECTOR_LENGTH_OVP.md.

Judges whether `text_length` (full token count under the detector's tokenizer) adds
Held-out Discriminative Gain beyond the baseline confidence B in predicting detector
correctness y, against the SAME cut points frozen by DETECTOR_OVP_CALIB.

  D > TAU_HI            -> Validated
  D < TAU_LO            -> Not-Validated   (mechanism-agnostic in v0.1)
  TAU_LO <= D <= TAU_HI -> Inconclusive
where D = median(HDG_AUC over R=200 stratified 50/50 PAIRED splits), no trimming.

Materialization: B, y, truncated are INHERITED + hash-verified from the calibration-
locked detector_per_example.csv (no model re-run). text_length is materialized fresh
via the pinned TOKENIZER (no model inference) over the hash-verified test set, and
cross-checked: 1[text_length>512] must equal the inherited `truncated` column, else abort.

NO-PEEKING: the --seed/--reps flags are determinism plumbing, NOT a smoke. Running this
script (any flags) always computes text_length's real HDG. The Section 8 smoke is a
SEPARATE synthetic harness that never materializes text_length. Single-execution under
seed 0x73C0DE. verify_cut_points() aborts on inheritance drift.
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
MASTER_SEED = 0x73C0DE
R = 200
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")

# ---- inherited cut points (sec 5), verbatim from the calibration result ----
TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
CALIB_RESULT_TAG = "detector-ovp-calib-result"
CALIB_RESULTS_JSON = os.path.join("..", "detector_truncation_ovp", "detector_calibration_results.json")

# ---- inherited substrate (sec 2) ----
INHERITED_PER_EXAMPLE = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
EXPECTED_PER_EXAMPLE_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"
DATA_CSV = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1", "chatgpt_detector_roberta_test_set.csv")
DATA_SHA256 = "a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47"
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
MAX_LEN = 512
LENGTH_CSV = "detector_length_per_example.csv"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_cut_points():
    """Abort if the hardcoded TAU_LO/TAU_HI have drifted from the calibration result."""
    if not os.path.exists(CALIB_RESULTS_JSON):
        raise SystemExit("ABORT: %s not found; cannot verify inherited cut points." % CALIB_RESULTS_JSON)
    cal = json.load(open(CALIB_RESULTS_JSON))
    if not (cal.get("tau_lo") == TAU_LO and cal.get("tau_hi") == TAU_HI):
        raise SystemExit("ABORT: hardcoded cut points (%r, %r) != calibration result (%r, %r); drift."
                         % (TAU_LO, TAU_HI, cal.get("tau_lo"), cal.get("tau_hi")))


def materialize():
    """Inherit B,y,truncated (hash-verified); materialize text_length via the pinned
    tokenizer; cross-check 1[text_length>512]==truncated; write the per-example file."""
    from transformers import AutoTokenizer

    actual = sha256_file(INHERITED_PER_EXAMPLE)
    if actual != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s; inherited substrate is not the "
                         "calibration-locked one." % (INHERITED_PER_EXAMPLE, actual, EXPECTED_PER_EXAMPLE_SHA256))
    base = pd.read_csv(INHERITED_PER_EXAMPLE)

    data_sha = sha256_file(DATA_CSV)
    if data_sha != DATA_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s." % (DATA_CSV, data_sha, DATA_SHA256))
    texts = pd.read_csv(DATA_CSV)[["id", "text"]]

    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    texts = texts.copy()
    texts["text_length"] = [len(tok(str(t), truncation=False)["input_ids"]) for t in texts["text"]]

    merged = base.merge(texts[["id", "text_length"]], on="id", how="left", validate="one_to_one")
    if merged["text_length"].isna().any():
        raise SystemExit("ABORT: text_length failed to align to all inherited rows by id.")

    # Integrity cross-check: 1[text_length>512] must reproduce the inherited truncated column.
    derived_trunc = (merged["text_length"] > MAX_LEN).astype(int)
    n_mismatch = int((derived_trunc != merged["truncated"].astype(int)).sum())
    if n_mismatch != 0:
        raise SystemExit("ABORT: 1[text_length>512] disagrees with inherited truncated in %d rows; "
                         "tokenizer/alignment/window mismatch." % n_mismatch)

    out = merged[["id", "B_confidence", "y_correct", "truncated", "text_length"]].copy()
    out.to_csv(LENGTH_CSV, index=False)
    return out, actual, sha256_file(LENGTH_CSV)


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
    ap.add_argument("--out", default="detector_length_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - NOT the locked run; STILL computes "
              "text_length's real HDG (NOT a no-peeking smoke).")
    if args.reps != R:
        print("[WARN] non-canonical reps %d (canonical R=%d) - NOT the locked run; STILL computes the "
              "real HDG (NOT a smoke)." % (args.reps, R))

    verify_cut_points()
    print("[1/2] materializing text_length (tokenizer) + inheriting B,y,truncated (hash-verified) ...")
    df, per_example_hash, length_hash = materialize()
    print("      inherited %s sha256=%s" % (INHERITED_PER_EXAMPLE, per_example_hash))
    print("      wrote %s sha256=%s" % (LENGTH_CSV, length_hash))
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    C = df["text_length"].to_numpy().astype(float)
    tl = df["text_length"].to_numpy()
    print("      n=%d accuracy=%.3f n_errors=%d  text_length[min/median/max]=%d/%d/%d  truncated_prev=%.3f" %
          (len(B), y.mean(), int((y == 0).sum()), tl.min(), int(np.median(tl)), tl.max(),
           (df["truncated"] == 1).mean()))

    print("[2/2] judging `text_length` against the inherited band over %d paired splits ..." % args.reps)
    res = judge(B, C, y, args.seed, args.reps)
    res["support_nongating"]["n_examples"] = int(len(B))
    res["support_nongating"]["n_errors"] = int((y == 0).sum())
    res["support_nongating"]["text_length_min"] = int(tl.min())
    res["support_nongating"]["text_length_median"] = float(np.median(tl))
    res["support_nongating"]["text_length_max"] = int(tl.max())
    res["support_nongating"]["truncated_prevalence"] = float((df["truncated"] == 1).mean())
    res["meta"] = {"candidate": "text_length", "baseline": "confidence (max softmax)",
                   "master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_canonical": R, "reps_used": args.reps,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "dataset_sha256": DATA_SHA256,
                   "inherited_per_example_sha256": per_example_hash,
                   "length_per_example_sha256": length_hash,
                   "estimator": ESTIMATOR_DESC,
                   "cut_points_provenance": CALIB_RESULT_TAG,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ["D_median_HDG_AUC", "verdict", "tau_lo", "tau_hi", "band_relation"]}, indent=2))


if __name__ == "__main__":
    main()
