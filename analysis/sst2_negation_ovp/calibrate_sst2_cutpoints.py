#!/usr/bin/env python3
"""
calibrate_sst2_cutpoints.py - SST2_OVP_CALIB cut-point calibration sub-study (lock 1).

Implements PRE_REGISTRATION_SST2_OVP_CALIB.md. Sets the SST-2-specific HDG cut
points (tau_lo, tau_hi) on the confidence/correctness substrate, OR reports
MIS-SPECIFIED if no valid band exists (a finding about the substrate, not a failure).

Two phases:
  (A) Materialize per-example (B=confidence, y=correctness) by running the pinned
      DistilBERT-SST2 model once over the pinned sst2_validation.csv. Writes
      sst2_per_example.csv + sha256 (inherited by lock 2).
  (B) Calibrate: over R_cal repeated STRATIFIED 50/50 train/test splits (the single
      resampling scheme; no bootstrap in this version), compute HDG for null and
      meaningful constructions; set tau_lo (max of nulls' P95) and tau_hi (3-step
      rule on the meaningful sweep); run the separability / mis-specification check.

Primary metric AUC; AP reported as a sensitivity panel (does not set cut points).
Single-execution: runs once under master seed 0x55712. Non-canonical --seed/--reps
are for pre-lock smoke testing only. Run from analysis/sst2_negation_ovp/ (DATA_CSV
is a relative path).

Persistence contract (pre-reg sec 7): the single run writes EVERYTHING needed to
audit it without a re-run — the full per-replication HDG arrays (AUC and AP, all
R_cal values per construction), null means (sec 6 check 3), all summary statistics,
and durable hashes (sst2_per_example_sha256.txt + results meta).
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split

# ---- pinned constants (pre-reg sec 3, 4, 5, 11) ----
MASTER_SEED = 0x55712
R_CAL = 200
DELTA = 0.01
SIGMA_M_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]   # meaningful sweep, uniform 0.5 spacing (larger = weaker)
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)

# ---- pinned model/data (sec 2). MODEL_REVISION is pinned to the DistilBERT-SST2
#      audit's revision SHA (model_revision.txt / calibration_summary.json); recorded
#      in the lock manifest and the results meta. ----
DATA_CSV = os.path.join("..", "..", "case_studies", "distilbert_sst2", "sst2_validation.csv")
MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"
MODEL_REVISION = "714eb0fa89d2f80546fda750413ed43d93601a13"   # pinned DistilBERT-SST2 revision, identical to the calibration audit (model_revision.txt / calibration_summary.json)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def materialize_per_example(out_csv="sst2_per_example.csv"):
    """Run the pinned DistilBERT-SST2 once -> per-example confidence B and correctness y."""
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    # Fail-fast input-data integrity check (belt-and-suspenders with the lock
    # manifest's abort path; activates even if the script is run outside the harness).
    hash_path = os.path.join(os.path.dirname(DATA_CSV), "sst2_validation_sha256.txt")
    expected = open(hash_path).read().strip().split()[0]
    actual = sha256_file(DATA_CSV)
    if actual != expected:
        raise SystemExit(
            "ABORT: input %s sha256 %s != pinned %s; substrate not byte-identical to "
            "the DistilBERT-SST2 audit data." % (DATA_CSV, actual, expected)
        )

    df = pd.read_csv(DATA_CSV)
    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model.eval()

    probs_pos = []
    with torch.no_grad():
        for i in range(0, len(df), 64):
            batch = df["sentence"].iloc[i:i + 64].tolist()
            enc = tok(batch, padding=True, truncation=True, max_length=128, return_tensors="pt")
            logits = model(**enc).logits
            p = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()   # P(POSITIVE) (label 1)
            probs_pos.extend(p.tolist())

    df = df.copy()
    df["p_pos"] = probs_pos
    df["pred"] = (df["p_pos"] >= 0.5).astype(int)
    df["B_confidence"] = np.maximum(df["p_pos"], 1.0 - df["p_pos"])   # max softmax prob
    df["y_correct"] = (df["pred"] == df["label"]).astype(int)
    df.to_csv(out_csv, index=False)
    return df


def hdg(B, C, y, rng, want_ap=False):
    """D = metric_test(logistic[B,C]) - metric_test(logistic[B]); stratified 50/50 split."""
    X1 = B.reshape(-1, 1)
    X2 = np.column_stack([B, C])
    ss = int(rng.integers(0, 2**31 - 1))
    X1tr, X1te, X2tr, X2te, ytr, yte = train_test_split(
        X1, X2, y, test_size=0.5, stratify=y, random_state=ss
    )
    p1 = LogisticRegression(**LOGIT_KW).fit(X1tr, ytr).predict_proba(X1te)[:, 1]
    p2 = LogisticRegression(**LOGIT_KW).fit(X2tr, ytr).predict_proba(X2te)[:, 1]
    d_auc = roc_auc_score(yte, p2) - roc_auc_score(yte, p1)
    if want_ap:
        # AP panel: ERROR is the positive class (rare). Relabel 1-y (1=error) and
        # score predicted error probability 1-P(correct). Non-gating; AUC sets cut points.
        d_ap = (average_precision_score(1 - yte, 1 - p2)
                - average_precision_score(1 - yte, 1 - p1))
        return d_auc, d_ap, roc_auc_score(yte, p1)
    return d_auc, None, roc_auc_score(yte, p1)


def construct(kind, param, B, y, rng):
    n = len(B)
    if kind == "null_redundant":
        return 2.0 * B - 1.0
    if kind == "null_noise":
        return rng.standard_normal(n)
    if kind == "meaningful":                      # param = sigma_m
        return y.astype(float) + rng.standard_normal(n) * param
    raise ValueError(kind)


def pctl(a, q):
    return float(np.percentile(a, q))   # numpy 'linear' (type-7), pinned


def calibrate(B, y, master_seed, reps):
    children = np.random.SeedSequence(master_seed).spawn(reps)
    cons = [("null_redundant", None), ("null_noise", None)] + [("meaningful", s) for s in SIGMA_M_GRID]
    hdg_auc = {(k, p): [] for k, p in cons}
    hdg_ap = {(k, p): [] for k, p in cons}
    base_auc = []
    for r in range(reps):
        rng = np.random.default_rng(children[r])
        for k, p in cons:
            C = construct(k, p, B, y, rng)
            d_auc, d_ap, b_auc = hdg(B, C, y, rng, want_ap=True)
            hdg_auc[(k, p)].append(d_auc)
            hdg_ap[(k, p)].append(d_ap)
            if k == "null_noise":
                base_auc.append(b_auc)
    hdg_auc = {k: np.array(v) for k, v in hdg_auc.items()}

    p95_red = pctl(hdg_auc[("null_redundant", None)], 95)
    p95_noise = pctl(hdg_auc[("null_noise", None)], 95)
    tau_lo = max(p95_red, p95_noise)

    # tau_hi: 3-step rule (pre-reg sec 5)
    meaningful_p5 = {s: pctl(hdg_auc[("meaningful", s)], 5) for s in SIGMA_M_GRID}
    clearing = [s for s in SIGMA_M_GRID if meaningful_p5[s] > tau_lo + DELTA]
    tau_hi = None
    sigma_m_at_tau_hi = None
    if clearing:
        sigma_m_at_tau_hi = max(clearing)          # largest sigma_m among clearing (weakest)
        tau_hi = meaningful_p5[sigma_m_at_tau_hi]

    meaningful_mean = {s: float(np.mean(hdg_auc[("meaningful", s)])) for s in SIGMA_M_GRID}
    null_mean_red = float(np.mean(hdg_auc[("null_redundant", None)]))
    null_mean_noise = float(np.mean(hdg_auc[("null_noise", None)]))
    desc = sorted(SIGMA_M_GRID, reverse=True)
    # monotonicity is NON-STRICT (<=) per pre-reg sec 6; nulls tolerance 1e-9 encodes "<= ~0"
    monotonic = all(meaningful_mean[a] <= meaningful_mean[b] for a, b in zip(desc, desc[1:]))
    nulls_nonpos = (null_mean_red <= 1e-9) and (null_mean_noise <= 1e-9)
    checks = {
        "1_tau_lo_positive": bool(tau_lo > 0),
        "2_band_exists": bool(tau_hi is not None and (tau_hi - tau_lo) >= DELTA),
        "3_monotonic_and_nulls_nonpositive": bool(monotonic and nulls_nonpos),
    }
    separable = all(checks.values())

    def cname(k, p):
        return k if p is None else "%s:%s" % (k, p)

    return {
        "tau_lo": tau_lo, "tau_hi": tau_hi, "sigma_m_at_tau_hi": sigma_m_at_tau_hi,
        "support": {
            "p95_null_redundant": p95_red, "p95_null_noise": p95_noise,
            "null_mean_AUC": {"null_redundant": null_mean_red, "null_noise": null_mean_noise},
            "meaningful_P5_AUC": {str(k): v for k, v in meaningful_p5.items()},
            "meaningful_mean_AUC": {str(k): v for k, v in meaningful_mean.items()},
            "baseline_auc_median_nullnoise_splits": float(np.median(base_auc)),  # baseline AUC(B->y) is construction-independent; sampled over the null-noise splits (pinned, pre-reg sec 7)
            "n_examples": int(len(B)), "n_errors": int((y == 0).sum()),
            "AP_sensitivity_panel": {cname(k, p): float(np.mean(v)) for (k, p), v in hdg_ap.items()},
        },
        # Full per-replication HDG arrays (pre-reg sec 7 persistence contract): the
        # single locked run must leave every distribution auditable without a re-run.
        "hdg_distributions": {
            "AUC": {cname(k, p): hdg_auc[(k, p)].tolist() for (k, p) in cons},
            "AP": {cname(k, p): [float(x) for x in hdg_ap[(k, p)]] for (k, p) in cons},
        },
        "separability_checks": checks,
        "SEPARABLE": separable,
        "verdict": "USABLE BAND" if separable else "MIS-SPECIFIED - substrate does not support clean HDG separation at this N (new lock required)",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED)
    ap.add_argument("--reps", type=int, default=R_CAL)
    ap.add_argument("--out", default="sst2_calibration_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - smoke only, NOT the locked run.")
    if args.reps != R_CAL:
        print("[WARN] non-canonical reps %d (canonical R_cal=%d) - smoke only, NOT the locked run." % (args.reps, R_CAL))

    print("[1/2] materializing per-example (B, y) from pinned DistilBERT-SST2 ...")
    df = materialize_per_example()
    per_example_hash = sha256_file("sst2_per_example.csv")
    with open("sst2_per_example_sha256.txt", "w") as f:   # durable hash (pre-reg sec 2/sec 7; inherited by lock 2)
        f.write(per_example_hash + "\n")
    print("      wrote sst2_per_example.csv  sha256=" + per_example_hash)
    print("      wrote sst2_per_example_sha256.txt")
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    print(f"      n={len(B)}, accuracy(mean y)={y.mean():.3f}, n_errors={(y==0).sum()}")

    print("[2/2] calibrating cut points over %d stratified splits ..." % args.reps)
    res = calibrate(B, y, args.seed, args.reps)
    res["meta"] = {"master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_cal_canonical": R_CAL, "reps_used": args.reps, "delta": DELTA,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "sst2_per_example_sha256": per_example_hash,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in
                      ["tau_lo", "tau_hi", "sigma_m_at_tau_hi", "separability_checks",
                       "SEPARABLE", "verdict"]}, indent=2))


if __name__ == "__main__":
    main()
