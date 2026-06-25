"""compute_core.py - shared PURE compute-core for DETECTOR_PERTURBATION_OVP (OVP #5).

Imported by BOTH the judge (sealed-loader, real candidate) and the smoke harness (synthetic-loader),
so the judge's exact compute path is exercised pre-lock on synthetic data (v0.2 template sec 1c).

Estimator is byte-identical to the calibration / #1-#4: StandardScaler -> LogisticRegression(lbfgs,
C=1.0, max_iter=1000, fit_intercept=True), out-of-sample AUC over R paired stratified 50/50 splits.

This core computes, on the SAME split per replication (so all share the identical baseline + partition):
  - real candidate   [B]      vs [B, C]          -> D = median HDG_AUC            (GATING)
  - permuted-C foil  [B]      vs [B, C_perm]     -> D_foil   (independent stream)  (non-gating)
  - confound-extended[B,Z]    vs [B, Z, C]       -> HDG_ext  (Z = length, domain)  (non-gating)
  - flip-rate panel  [B]      vs [B, C_alt]      -> D_alt                          (non-gating)

PURE: no file/network IO, no global entropy. Deterministic in master_seed.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FOIL_SEED_XOR = 0xF011
LOGIT_KW = dict(solver="lbfgs", C=1.0, max_iter=1000, fit_intercept=True)
ESTIMATOR_DESC = ("StandardScaler(with_mean=True, with_std=True, train-fit) -> "
                  "LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)")


def _fitp(Xtr, ytr, Xte):
    return make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW)).fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def verdict_of(D, tau_lo, tau_hi):
    if D > tau_hi:
        return "Validated"
    if D < tau_lo:
        return "Not-Validated"
    return "Inconclusive"


def compute_sealed(B, y, C, C_alt, Z, tau_lo, tau_hi, eps_confound, master_seed, reps=200):
    """Returns the full sealed result dict. Z is the (n,k) confound covariate matrix [length, domain_onehot]."""
    B = np.asarray(B, float); y = np.asarray(y, int); C = np.asarray(C, float)
    C_alt = np.asarray(C_alt, float); Z = np.asarray(Z, float)
    if Z.ndim == 1:
        Z = Z.reshape(-1, 1)
    n = len(B)
    children = np.random.SeedSequence(master_seed).spawn(reps)
    foil_children = np.random.SeedSequence(master_seed ^ FOIL_SEED_XOR).spawn(reps)
    X_B = B.reshape(-1, 1)
    X_BC = np.column_stack([B, C])
    X_Balt = np.column_stack([B, C_alt])
    X_BZ = np.column_stack([B, Z])
    X_BZC = np.column_stack([B, Z, C])

    d_auc = np.empty(reps); d_ap = np.empty(reps)
    foil_auc = np.empty(reps); ext_hdg = np.empty(reps); alt_auc = np.empty(reps)
    for r in range(reps):
        rng = np.random.default_rng(children[r])
        ss = int(rng.integers(0, 2**31 - 1))
        tr, te = train_test_split(np.arange(n), test_size=0.5, stratify=y, random_state=ss)
        ytr, yte = y[tr], y[te]
        # baseline [B] (shared by real candidate, foil, sensitivity)
        p1 = _fitp(X_B[tr], ytr, X_B[te]); auc1 = roc_auc_score(yte, p1)
        ap1 = average_precision_score(1 - yte, 1 - p1)
        # real candidate [B, C]  (GATING)
        p2 = _fitp(X_BC[tr], ytr, X_BC[te])
        d_auc[r] = roc_auc_score(yte, p2) - auc1
        d_ap[r] = average_precision_score(1 - yte, 1 - p2) - ap1
        # permuted-C foil [B, C_perm], independent stream, SAME split
        frng = np.random.default_rng(foil_children[r])
        Cperm = C.copy(); frng.shuffle(Cperm)
        pf = _fitp(np.column_stack([B, Cperm])[tr], ytr, np.column_stack([B, Cperm])[te])
        foil_auc[r] = roc_auc_score(yte, pf) - auc1
        # flip-rate sensitivity [B, C_alt]
        pa = _fitp(X_Balt[tr], ytr, X_Balt[te]); alt_auc[r] = roc_auc_score(yte, pa) - auc1
        # confound-extended: C beyond [B, Z]
        pbz = _fitp(X_BZ[tr], ytr, X_BZ[te]); auc_bz = roc_auc_score(yte, pbz)
        pbzc = _fitp(X_BZC[tr], ytr, X_BZC[te]); ext_hdg[r] = roc_auc_score(yte, pbzc) - auc_bz

    D = float(np.median(d_auc)); D_foil = float(np.median(foil_auc))
    HDG_ext = float(np.median(ext_hdg)); D_alt = float(np.median(alt_auc))
    confound_gap = D - HDG_ext
    return {
        "D_median_HDG_AUC": D, "verdict": verdict_of(D, tau_lo, tau_hi),
        "tau_lo": tau_lo, "tau_hi": tau_hi,
        "band_relation": {"D_gt_tau_hi": bool(D > tau_hi), "D_lt_tau_lo": bool(D < tau_lo),
                          "D_in_band": bool(tau_lo <= D <= tau_hi)},
        "support_nongating": {
            "HDG_AUC_mean": float(np.mean(d_auc)), "HDG_AUC_P5": float(np.percentile(d_auc, 5)),
            "HDG_AUC_P95": float(np.percentile(d_auc, 95)),
            "frac_reps_above_tau_hi": float(np.mean(d_auc > tau_hi)),
            "frac_reps_below_tau_lo": float(np.mean(d_auc < tau_lo)),
            "frac_reps_in_band": float(np.mean((d_auc >= tau_lo) & (d_auc <= tau_hi))),
            "AP_error_class_median": float(np.median(d_ap)),
            # permuted-C foil (non-gating; sec 4/6)
            "foil_D_median": D_foil, "foil_verdict": verdict_of(D_foil, tau_lo, tau_hi),
            "foil_HDG_mean": float(np.mean(foil_auc)), "foil_HDG_P5": float(np.percentile(foil_auc, 5)),
            "foil_HDG_P95": float(np.percentile(foil_auc, 95)),
            "foil_frac_above_tau_hi": float(np.mean(foil_auc > tau_hi)),
            "foil_frac_below_tau_lo": float(np.mean(foil_auc < tau_lo)),
            "foil_frac_in_band": float(np.mean((foil_auc >= tau_lo) & (foil_auc <= tau_hi))),
            "foil_pre_commitment_met": bool(D_foil < tau_lo),
            "foil_clears_tau_lo": bool(D_foil >= tau_lo),   # True -> sec 6 RED-FLAG caveat
            # confound diagnostic (non-gating; sec 6): C beyond [B, length, domain]
            "confound_HDG_extended_median": HDG_ext, "confound_gap": float(confound_gap),
            "confound_genuine": bool(confound_gap <= eps_confound),  # False -> length/domain-proxy caveat
            "eps_confound": eps_confound,
            # flip-rate sensitivity (non-gating)
            "flip_rate_D_median": D_alt, "flip_rate_verdict": verdict_of(D_alt, tau_lo, tau_hi),
        },
        "hdg_distribution": {"AUC": d_auc.tolist(), "AP_error_class": d_ap.tolist(),
                             "foil_AUC": foil_auc.tolist(), "confound_ext_HDG": ext_hdg.tolist(),
                             "flip_rate_AUC": alt_auc.tolist()},
    }
