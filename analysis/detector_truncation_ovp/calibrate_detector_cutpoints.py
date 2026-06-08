#!/usr/bin/env python3
"""
calibrate_detector_cutpoints.py - DETECTOR_OVP_CALIB cut-point calibration (lock 1).
Implements PRE_REGISTRATION_DETECTOR_OVP_CALIB.md.

Substrate: ChatGPT-detector RoBERTa over the hashed RAID test subsample (the first
substrate to PASS the empirical noise-null eligibility screen). Estimator: the
SST-2 v2 validated instantiation -- StandardScaler (train-fit) -> L2 logistic.
Sets tau_lo, tau_hi on the confidence/correctness substrate OR reports MIS-SPECIFIED.

Phases:
  (A) Materialize per-example (B=confidence, y=correctness, truncated) by running the
      pinned RoBERTa once over the hashed test set. Writes detector_per_example.csv +
      sha256. truncated is the LOCK-2 candidate: stored here, NOT used in calibration.
      Determinism cross-check against the audit's predictions.csv (abort on mismatch).
  (B) Calibrate: R_cal stratified 50/50 splits; standardized HDG for null/meaningful
      constructions; tau_lo (max of nulls' P95), tau_hi (3-step rule); separability.

Primary metric AUC; AP (error-class) reported, non-gating. Single-execution under
seed 0xD37EC7; non-canonical --seed/--reps are smoke-only. Run from this directory.
Persistence contract (pre-reg sec 7): full per-replication HDG arrays, null means,
all summaries, durable hashes.
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

# ---- pinned constants (pre-reg sec 3, 4, 5, 11) ----
MASTER_SEED = 0xD37EC7
R_CAL = 200
DELTA = 0.01
EPS_NULL = DELTA   # check-3 null-mean one-sided tolerance (pre-reg sec 6.3): encodes "<= ~0"
                   # as "<= delta" so an eligible substrate's zero-centered null isn't rejected
                   # on the sign of sampling noise. One-sided: a negative null still passes.
SIGMA_M_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")

# ---- pinned substrate (sec 2) ----
AUDIT_DIR = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1")
DATA_CSV = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set.csv")
DATA_SHA256 = "a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47"
AUDIT_PREDICTIONS = os.path.join(AUDIT_DIR, "predictions.csv")
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
AI_CLASS_INDEX = 1          # id2label = {0: Human, 1: ChatGPT}
MAX_LEN = 512


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def materialize_per_example(out_csv="detector_per_example.csv"):
    """Run pinned RoBERTa once -> per-example B, y, truncated. Cross-check vs audit."""
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    actual = sha256_file(DATA_CSV)
    if actual != DATA_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s." % (DATA_CSV, actual, DATA_SHA256))

    df = pd.read_csv(DATA_CSV)
    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model.eval()

    p_ai, trunc = [], []
    with torch.no_grad():
        for text in df["text"].astype(str).tolist():
            enc = tok(text, return_tensors="pt", truncation=True, max_length=MAX_LEN, padding=False)
            full = tok(text, truncation=False, padding=False)
            trunc.append(int(len(full["input_ids"]) > MAX_LEN))
            probs = torch.softmax(model(**enc).logits[0], dim=-1)
            p_ai.append(float(probs[AI_CLASS_INDEX]))

    out = df[["id", "is_ai_generated", "source_domain"]].copy()
    out["predicted_prob_ai"] = p_ai
    out["pred"] = (out["predicted_prob_ai"] >= 0.5).astype(int)
    out["B_confidence"] = np.maximum(out["predicted_prob_ai"], 1.0 - out["predicted_prob_ai"])
    out["y_correct"] = (out["pred"] == out["is_ai_generated"].astype(int)).astype(int)
    out["truncated"] = trunc

    # Determinism cross-check vs the audit predictions.csv (deterministic inference).
    if os.path.exists(AUDIT_PREDICTIONS):
        aud = pd.read_csv(AUDIT_PREDICTIONS).set_index("id")
        m = out.set_index("id").join(aud[["predicted_prob_ai", "truncated"]], rsuffix="_aud")
        dp = np.abs(m["predicted_prob_ai"] - m["predicted_prob_ai_aud"]).max()
        dt = int((m["truncated"] != m["truncated_aud"]).sum())
        if dp > 1e-5 or dt > 0:
            raise SystemExit("ABORT: materialization disagrees with audit predictions.csv "
                             "(max|dprob|=%.2e, truncated mismatches=%d)." % (dp, dt))
        print("      determinism cross-check vs audit predictions.csv OK (max|dprob|=%.2e)" % dp)

    out.to_csv(out_csv, index=False)
    return out


def estimator():
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))


def hdg(B, C, y, rng, want_ap=False):
    X1 = B.reshape(-1, 1)
    X2 = np.column_stack([B, C])
    ss = int(rng.integers(0, 2**31 - 1))
    X1tr, X1te, X2tr, X2te, ytr, yte = train_test_split(
        X1, X2, y, test_size=0.5, stratify=y, random_state=ss
    )
    p1 = estimator().fit(X1tr, ytr).predict_proba(X1te)[:, 1]
    p2 = estimator().fit(X2tr, ytr).predict_proba(X2te)[:, 1]
    d_auc = roc_auc_score(yte, p2) - roc_auc_score(yte, p1)
    if want_ap:
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
    if kind == "meaningful":
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

    meaningful_p5 = {s: pctl(hdg_auc[("meaningful", s)], 5) for s in SIGMA_M_GRID}
    clearing = [s for s in SIGMA_M_GRID if meaningful_p5[s] > tau_lo + DELTA]
    tau_hi = None
    sigma_m_at_tau_hi = None
    if clearing:
        sigma_m_at_tau_hi = max(clearing)
        tau_hi = meaningful_p5[sigma_m_at_tau_hi]

    meaningful_mean = {s: float(np.mean(hdg_auc[("meaningful", s)])) for s in SIGMA_M_GRID}
    null_mean_red = float(np.mean(hdg_auc[("null_redundant", None)]))
    null_mean_noise = float(np.mean(hdg_auc[("null_noise", None)]))
    desc = sorted(SIGMA_M_GRID, reverse=True)
    monotonic = all(meaningful_mean[a] <= meaningful_mean[b] for a, b in zip(desc, desc[1:]))
    # check-3 null condition: nulls must not AVERAGE a gain reaching the decision margin
    # (one-sided tolerance EPS_NULL=DELTA; pre-reg sec 6.3). A negative null mean passes.
    nulls_nonpos = (null_mean_red <= EPS_NULL) and (null_mean_noise <= EPS_NULL)
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
            "baseline_auc_median_nullnoise_splits": float(np.median(base_auc)),  # construction-independent; sec 7
            "n_examples": int(len(B)), "n_errors": int((y == 0).sum()),
            "AP_sensitivity_panel": {cname(k, p): float(np.mean(v)) for (k, p), v in hdg_ap.items()},
        },
        "hdg_distributions": {
            "AUC": {cname(k, p): hdg_auc[(k, p)].tolist() for (k, p) in cons},
            "AP": {cname(k, p): [float(x) for x in hdg_ap[(k, p)]] for (k, p) in cons},
        },
        "separability_checks": checks,
        "SEPARABLE": separable,
        "verdict": "USABLE BAND" if separable else "MIS-SPECIFIED - substrate does not support clean HDG separation at this N under this estimator (new lock required)",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=MASTER_SEED)
    ap.add_argument("--reps", type=int, default=R_CAL)
    ap.add_argument("--out", default="detector_calibration_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - smoke only, NOT the locked run.")
    if args.reps != R_CAL:
        print("[WARN] non-canonical reps %d (canonical R_cal=%d) - smoke only, NOT the locked run." % (args.reps, R_CAL))

    print("[1/2] materializing per-example (B, y, truncated) from pinned RoBERTa ...")
    df = materialize_per_example()
    per_example_hash = sha256_file("detector_per_example.csv")
    with open("detector_per_example_sha256.txt", "w") as f:
        f.write(per_example_hash + "\n")
    print("      wrote detector_per_example.csv  sha256=" + per_example_hash)
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    print(f"      n={len(B)}, accuracy(mean y)={y.mean():.3f}, n_errors={(y==0).sum()}, truncated_frac={df['truncated'].mean():.3f}")

    print("[2/2] calibrating cut points over %d stratified splits (standardized estimator) ..." % args.reps)
    res = calibrate(B, y, args.seed, args.reps)
    res["meta"] = {"master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_cal_canonical": R_CAL, "reps_used": args.reps, "delta": DELTA,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "dataset_sha256": DATA_SHA256,
                   "detector_per_example_sha256": per_example_hash,
                   "estimator": ESTIMATOR_DESC,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in
                      ["tau_lo", "tau_hi", "sigma_m_at_tau_hi", "separability_checks",
                       "SEPARABLE", "verdict"]}, indent=2))


if __name__ == "__main__":
    main()
