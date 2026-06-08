#!/usr/bin/env python3
"""
calibrate_sst2_cutpoints_v2.py - SST2_OVP_CALIB_v2 cut-point calibration (standardized
estimator instantiation). Implements PRE_REGISTRATION_SST2_OVP_CALIB_v2.md.

Single pinned change from v1: the HDG estimator standardizes features (StandardScaler,
fit on the TRAIN partition only) before the L2 logistic. Everything else is held
identical to v1, INCLUDING the master seed (0x55712), so v1->v2 is a controlled
one-variable contrast.

Materialization is INHERITED, not re-run: v2 reads the v1-locked sst2_per_example.csv
and verifies its sha256 against the pinned hash (no DistilBERT/torch needed). Because
standardization lives inside the estimator, (B, y) are byte-identical to v1.

Sets tau_lo, tau_hi on the confidence/correctness substrate OR reports MIS-SPECIFIED.
Primary metric AUC; AP (error-class) reported as a non-gating sensitivity panel.
Single-execution under seed 0x55712; non-canonical --seed/--reps are smoke-only.
Run from analysis/sst2_negation_ovp/.

Persistence contract (pre-reg sec 7): writes the full per-replication HDG arrays
(AUC and AP), null means, all summaries, and meta incl. the inherited per-example hash
and the estimator descriptor -- everything needed to audit the run without a re-run.
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
MASTER_SEED = 0x55712
R_CAL = 200
DELTA = 0.01
SIGMA_M_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]   # meaningful sweep, uniform 0.5 spacing
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")

# ---- pinned substrate (sec 2): inherited from the v1 lock, hash-verified. ----
MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"
MODEL_REVISION = "714eb0fa89d2f80546fda750413ed43d93601a13"
PER_EXAMPLE_CSV = "sst2_per_example.csv"                    # v1-locked materialization
PER_EXAMPLE_HASH_FILE = "sst2_per_example_sha256.txt"
EXPECTED_PER_EXAMPLE_SHA256 = "e9e5b12a6e1c1dbb0d5ea664e469116bb075c9060f3f78fe09dc0e7cb7bec1c7"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inherited_per_example():
    """Read the v1-locked per-example (B, y); verify sha256 against the pinned anchor
    AND the recorded hash file. No model re-run (sec 2). Abort on any mismatch."""
    actual = sha256_file(PER_EXAMPLE_CSV)
    if actual != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit(
            "ABORT: %s sha256 %s != pinned %s; inherited materialization is not the "
            "v1-locked substrate." % (PER_EXAMPLE_CSV, actual, EXPECTED_PER_EXAMPLE_SHA256)
        )
    if os.path.exists(PER_EXAMPLE_HASH_FILE):
        recorded = open(PER_EXAMPLE_HASH_FILE).read().strip().split()[0]
        if recorded != actual:
            raise SystemExit(
                "ABORT: %s (%s) disagrees with %s (%s)." %
                (PER_EXAMPLE_HASH_FILE, recorded, PER_EXAMPLE_CSV, actual)
            )
    df = pd.read_csv(PER_EXAMPLE_CSV)
    return df, actual


def estimator():
    """The v2 pin: StandardScaler (train-fit) -> L2 logistic. fit() learns the scaler
    on the training rows only; transform applies train stats to the held-out rows."""
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))


def hdg(B, C, y, rng, want_ap=False):
    """D = metric_test(pipe[B,C]) - metric_test(pipe[B]); stratified 50/50 split.
    Each pipeline standardizes its own columns using TRAIN-fit statistics (no leakage)."""
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
        # AP panel: ERROR is the positive class. Relabel 1-y, score 1-P(correct).
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
            "baseline_auc_median_nullnoise_splits": float(np.median(base_auc)),  # construction-independent; sampled over null-noise splits (pinned, sec 7). EXPECTED ~0.86 (sec 3 invariant 1)
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
    ap.add_argument("--out", default="sst2_calibration_v2_results.json")
    args = ap.parse_args()
    if args.seed != MASTER_SEED:
        print("[WARN] non-canonical seed " + hex(args.seed) + " - smoke only, NOT the locked run.")
    if args.reps != R_CAL:
        print("[WARN] non-canonical reps %d (canonical R_cal=%d) - smoke only, NOT the locked run." % (args.reps, R_CAL))

    print("[1/2] loading inherited per-example (B, y) from the v1 lock (hash-verified) ...")
    df, per_example_hash = load_inherited_per_example()
    print("      verified %s  sha256=%s" % (PER_EXAMPLE_CSV, per_example_hash))
    B = df["B_confidence"].to_numpy()
    y = df["y_correct"].to_numpy()
    print(f"      n={len(B)}, accuracy(mean y)={y.mean():.3f}, n_errors={(y==0).sum()}")

    print("[2/2] calibrating cut points over %d stratified splits (standardized estimator) ..." % args.reps)
    res = calibrate(B, y, args.seed, args.reps)
    res["meta"] = {"master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(args.seed),
                   "R_cal_canonical": R_CAL, "reps_used": args.reps, "delta": DELTA,
                   "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                   "sst2_per_example_sha256": per_example_hash,
                   "estimator": ESTIMATOR_DESC,
                   "generated_utc": datetime.now(timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in
                      ["tau_lo", "tau_hi", "sigma_m_at_tau_hi", "separability_checks",
                       "SEPARABLE", "verdict"]}, indent=2))


if __name__ == "__main__":
    main()
