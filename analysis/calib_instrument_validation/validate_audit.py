#!/usr/bin/env python3
"""
validate_audit.py — Instrument validation (positive control) for the AEPF
calibration-audit decision rule.

This is METHODS-LEVEL INSTRUMENT VALIDATION, not a locked AEPF study. It does not
test a hypothesis about the world; it confirms that the calibration-audit decision
rule used in the real model audits (AI-calibration template §5-6) returns a POSITIVE
verdict on synthetic data that is calibrated by construction, and REJECTS synthetic
data that is miscalibrated by construction — and it characterizes the operating
characteristics (classification rates) across 100 replications.

Decision rule (AI-calibration template §5-6, reproduced verbatim):
  - K = 10 equal-width bins on the predicted-probability axis.
  - Per bin: n, mean predicted probability, observed positive frequency, and the
    Wilson 95% confidence interval on the observed frequency.
  - A bin "passes" iff n >= 30 AND the bin's mean predicted probability lies inside
    the Wilson 95% CI of its observed frequency. Bins with n < 30 are excluded from
    the count (denominator = K minus excluded bins).
  - Brier Skill Score (BSS) vs base-rate climatology = 1 - Brier_model/Brier_clim.
  - Outcome:
      Calibrated (strong)      : >= 9 bins pass AND BSS > 0
      Calibrated (acceptable)  : >= 7 bins pass AND BSS > 0
      Not calibrated           : < 5 bins pass
      Calibration drift detected: otherwise (5-6 bins pass, or BSS <= 0)

Arms (pre-committed before running):
  POSITIVE controls (must be classified Calibrated) — predictions drawn from a
    realistic spread, outcomes drawn FROM the predictions, so calibration holds
    exactly by construction at arbitrary spread:
      calibrated_uniform   : pred ~ Beta(1,1)      [= Uniform], y ~ Bernoulli(pred)
      calibrated_asym      : pred ~ Beta(2,5),                  y ~ Bernoulli(pred)
      calibrated_bimodal   : pred ~ Beta(0.5,0.5),              y ~ Bernoulli(pred)
  TOLERANCE characterization (informative, NOT gating) — a noisy ESTIMATOR of a
    latent truth; calibrated only asymptotically, O(sigma^2) bias under finite noise:
      noisy_sigma_{0.25,0.5,1.0,2.0}: latent p~U(0,1); pred=sigmoid(logit(p)+N(0,s));
                                       y ~ Bernoulli(p)
  NEGATIVE controls (must be REJECTED = drift or not-calibrated) — miscalibration
    by construction; latent p~U(0,1), y~Bernoulli(p), prediction distorted:
      overconfident_T0.5   : pred = sigmoid(logit(p)/0.5)   [temperature-scaled]
      underconfident_T2.0  : pred = sigmoid(logit(p)/2.0)   [temperature-scaled]
      shift_pos_b+0.5      : pred = sigmoid(logit(p)+0.5)   [systematic logit bias]
      shift_neg_b-0.5      : pred = sigmoid(logit(p)-0.5)   [systematic logit bias]

Scope note: the negative controls test TEMPERATURE-SCALED and SYSTEMATIC-LOGIT-SHIFT
miscalibration specifically. They do not establish that the audit catches every
possible miscalibration (e.g., difficulty-stratified). The claim is bounded to the
parametric failure families enumerated above.

Pre-committed success criteria (grounded by the single-replication pilot, which
scored 10/10 bins on a calibrated arm — far above the 7-bin 'acceptable' line —
implying a per-replication positive-classification probability near 1; 90/100 is a
conservative floor that still pre-commits a falsifiable bar):
  - Each POSITIVE arm: classified Calibrated (strong or acceptable) in >= 90/100 reps.
  - Each NEGATIVE arm: classified rejected (drift or not-calibrated) in >= 90/100 reps.
  - TOLERANCE arms: reported, not gated.

Determinism: master seed 0x1DEA; per (replication r, arm a) the stream is
np.random.default_rng([MASTER_SEED, r, a]) so arms are independent and arm order
does not affect results.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MASTER_SEED = 0x1DEA
R = 100          # replications
N = 4000         # examples per arm per replication
K = 10           # reliability bins
Z = 1.959963985  # 95% normal quantile

OUT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------- decision rule
def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """Wilson 95% CI on a proportion given k successes of n."""
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    d = 1.0 + z * z / n
    center = (ph + z * z / (2 * n)) / d
    half = (z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))) / d
    return (center - half, center + half)


def audit(pred: np.ndarray, y: np.ndarray, K: int = K):
    """Return (verdict, bins_passed, bins_counted, bss) per template §5-6."""
    pred = np.clip(pred, 0.0, 1.0)
    base = float(y.mean())
    brier_m = float(np.mean((pred - y) ** 2))
    brier_c = float(np.mean((base - y) ** 2))
    bss = 1.0 - brier_m / brier_c if brier_c > 0 else 0.0
    binidx = np.minimum((pred * K).astype(int), K - 1)
    passes = 0
    counted = 0
    for b in range(K):
        m = binidx == b
        n = int(m.sum())
        if n < 30:
            continue
        counted += 1
        mean_pred = float(pred[m].mean())
        lo, hi = wilson(int(y[m].sum()), n)
        if lo <= mean_pred <= hi:
            passes += 1
    if passes < 5:
        verdict = "Not calibrated"
    elif bss <= 0:
        verdict = "Calibration drift detected"
    elif passes >= 9:
        verdict = "Calibrated (strong)"
    elif passes >= 7:
        verdict = "Calibrated (acceptable)"
    else:
        verdict = "Calibration drift detected"
    return verdict, passes, counted, bss


# --------------------------------------------------------------------- the arms
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def arm_calibrated(rng, a, b):
    pred = rng.beta(a, b, N)
    y = (rng.uniform(size=N) < pred).astype(float)
    return pred, y


def arm_noisy(rng, sigma):
    p = rng.uniform(size=N)
    pred = _sigmoid(_logit(p) + rng.normal(0.0, sigma, N))
    y = (rng.uniform(size=N) < p).astype(float)
    return pred, y


def arm_temp(rng, T):
    p = rng.uniform(size=N)
    pred = _sigmoid(_logit(p) / T)
    y = (rng.uniform(size=N) < p).astype(float)
    return pred, y


def arm_shift(rng, b):
    p = rng.uniform(size=N)
    pred = _sigmoid(_logit(p) + b)
    y = (rng.uniform(size=N) < p).astype(float)
    return pred, y


ARMS = [
    ("calibrated_uniform",   "POSITIVE",  lambda rng: arm_calibrated(rng, 1.0, 1.0)),
    ("calibrated_asym",      "POSITIVE",  lambda rng: arm_calibrated(rng, 2.0, 5.0)),
    ("calibrated_bimodal",   "POSITIVE",  lambda rng: arm_calibrated(rng, 0.5, 0.5)),
    ("noisy_sigma_0.25",     "TOLERANCE", lambda rng: arm_noisy(rng, 0.25)),
    ("noisy_sigma_0.5",      "TOLERANCE", lambda rng: arm_noisy(rng, 0.5)),
    ("noisy_sigma_1.0",      "TOLERANCE", lambda rng: arm_noisy(rng, 1.0)),
    ("noisy_sigma_2.0",      "TOLERANCE", lambda rng: arm_noisy(rng, 2.0)),
    ("overconfident_T0.5",   "NEGATIVE",  lambda rng: arm_temp(rng, 0.5)),
    ("underconfident_T2.0",  "NEGATIVE",  lambda rng: arm_temp(rng, 2.0)),
    ("shift_pos_b+0.5",      "NEGATIVE",  lambda rng: arm_shift(rng, 0.5)),
    ("shift_neg_b-0.5",      "NEGATIVE",  lambda rng: arm_shift(rng, -0.5)),
]

CATS = ["Calibrated (strong)", "Calibrated (acceptable)",
        "Calibration drift detected", "Not calibrated"]
CALIBRATED = {"Calibrated (strong)", "Calibrated (acceptable)"}


def main() -> int:
    results = {}
    for ai, (name, kind, draw) in enumerate(ARMS):
        counts = {c: 0 for c in CATS}
        bins_passed = []
        bsss = []
        for r in range(R):
            rng = np.random.default_rng([MASTER_SEED, r, ai])
            pred, y = draw(rng)
            verdict, passes, counted, bss = audit(pred, y)
            counts[verdict] += 1
            bins_passed.append(passes)
            bsss.append(bss)
        pct_cal = 100.0 * sum(counts[c] for c in CALIBRATED) / R
        pct_rej = 100.0 - pct_cal
        results[name] = {
            "kind": kind, "counts": counts,
            "pct_calibrated": pct_cal, "pct_rejected": pct_rej,
            "mean_bins_passed": float(np.mean(bins_passed)),
            "mean_bss": float(np.mean(bsss)),
        }

    # ---- pre-committed success evaluation
    pos_ok = all(results[n]["pct_calibrated"] >= 90.0
                 for n, k, _ in ARMS if k == "POSITIVE")
    neg_ok = all(results[n]["pct_rejected"] >= 90.0
                 for n, k, _ in ARMS if k == "NEGATIVE")
    overall = "PASS" if (pos_ok and neg_ok) else "FAIL"

    # ---- render markdown operating-characteristic table
    lines = []
    lines.append("# Instrument Validation — AEPF calibration audit (operating characteristics)")
    lines.append("")
    lines.append(f"**Replications:** {R}  |  **N per arm:** {N}  |  **K bins:** {K}  "
                 f"|  **master seed:** {hex(MASTER_SEED)}")
    lines.append("**Decision rule:** AI-calibration template §5-6 (verbatim).")
    lines.append("")
    lines.append(f"## Verdict: **{overall}**")
    lines.append("")
    lines.append("Positive arms classified Calibrated in >=90/100, and negative arms "
                 "rejected in >=90/100." if overall == "PASS" else
                 "A pre-committed criterion was not met (see table).")
    lines.append("")
    lines.append("| arm | kind | % Calibrated | % Rejected | mean bins passed (/10) | mean BSS |")
    lines.append("|---|---|---|---|---|---|")
    for name, kind, _ in ARMS:
        r = results[name]
        lines.append(f"| {name} | {kind} | {r['pct_calibrated']:.0f} | "
                     f"{r['pct_rejected']:.0f} | {r['mean_bins_passed']:.1f} | "
                     f"{r['mean_bss']:.3f} |")
    lines.append("")
    lines.append("### Outcome breakdown (counts over 100 replications)")
    lines.append("")
    lines.append("| arm | strong | acceptable | drift | not-calibrated |")
    lines.append("|---|---|---|---|---|")
    for name, kind, _ in ARMS:
        c = results[name]["counts"]
        lines.append(f"| {name} | {c['Calibrated (strong)']} | "
                     f"{c['Calibrated (acceptable)']} | "
                     f"{c['Calibration drift detected']} | {c['Not calibrated']} |")
    lines.append("")
    lines.append("*Methods-level instrument validation, not a locked AEPF study. "
                 "Negative controls cover temperature-scaled and logit-shift "
                 "miscalibration families only.*")
    md = "\n".join(lines)

    (OUT_DIR / "validation_results.json").write_text(
        json.dumps({"overall": overall, "config": {"R": R, "N": N, "K": K,
                    "master_seed": hex(MASTER_SEED)}, "arms": results}, indent=2))
    (OUT_DIR / "VALIDATION_RESULTS.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[validate] wrote VALIDATION_RESULTS.md and validation_results.json -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
