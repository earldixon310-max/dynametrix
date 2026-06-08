# Script-build findings — calibrate_sst2_cutpoints_v2.py vs the SST2_OVP_CALIB_v2 pre-reg

Per the codified build-and-smoke precondition: script built strictly to the v2 pre-reg, then smoke-tested on a non-canonical seed **before** cold-pass routing. Because the v1-locked `sst2_per_example.csv` is available, the smoke ran the v2 logic mirror on the **real compressed `(B, y)`** (numpy-only IRLS logistic + train-fit z-scoring), not simulated data — a much stronger smoke than v1's.

## Build conformance

`calibrate_sst2_cutpoints_v2.py` compiles clean. The single pin change is in `hdg()`: `estimator()` returns `make_pipeline(StandardScaler(), LogisticRegression(**LOGIT_KW))`, fit per split (scaler train-fit, applied to held-out) — leak-free. Materialization is inherited (`load_inherited_per_example()` reads the v1-locked CSV, verifies sha256 against the pinned anchor `e9e5b12a…b7bec1c7` and the recorded hash file, aborts on mismatch; verified PASS against the real file). Seed `0x55712` held identical to v1. Output `sst2_calibration_v2_results.json`; meta adds the estimator descriptor.

## Smoke 1 — invariants (both HOLD)

On the real `(B, y)`, numpy mirror, non-canonical seed `0xBEEF`:
- **Invariant 2 (redundant null ≡ 0):** `max|HDG| = 0.00e+00` across 200 reps — the two standardized columns are identical, ranking-invariant. ✓
- **Invariant 1 (baseline AUC unchanged):** standardized baseline `AUC(B→y)` median **0.8623** ≈ v1's 0.86 — standardizing one feature is monotone, ranking preserved. ✓

The mirror also **reproduces v1's known unstandardized noise null** (mean −0.230 / P95 −0.091 vs the locked −0.240 / −0.086), confirming the mirror is faithful enough to trust directionally.

## Smoke 2 — the v2 question: does standardization re-center the noise null? **Largely NO.**

Standardization **helped but did not cross zero.** Noise null moved from v1's (mean −0.240, P95 −0.086) to **(mean −0.140, P95 −0.023)** — ~73% of the way to zero, still **98% ≤ 0**. So `τ_lo = max(0, −0.023) = 0`, **check 1 still fails → MIS-SPECIFIED via the same door as v1.**

## Smoke 3 — is it a tuning problem? Regularization sweep says NO (structural)

Standardized estimator, noise null P95 across L2 strength (need P95 > 0 for `τ_lo > 0`):

| C | λ=1/C | noise null mean | noise null P95 | τ_lo>0? |
|---|---|---|---|---|
| 1.0 | 1 | −0.136 | −0.0298 | no |
| 0.1 | 10 | −0.127 | −0.0168 | no |
| 0.03 | 33 | −0.116 | −0.0120 | no |
| 0.01 | 100 | −0.105 | −0.0159 | no |
| 0.001 | 1000 | −0.101 | −0.0122 | no |

Stronger regularization shrinks the magnitude but **plateaus around −0.011 and never crosses zero**. No setting in the standardize + L2 family produces a strictly-positive floor.

## Diagnosis — the binding constraint is the tiny error class, not (only) compression

v1 attributed `τ_lo = 0` to confidence compression. The smoke refines that: standardization fully addressed compression (baseline AUC unchanged; null mean improved −0.24→−0.14) yet the floor stayed at 0. The **residual, irreducible driver is the minority (error) class size** — 78 errors total, ~39 per 50/50 split. With so few minority points, adding *any* irrelevant feature to the logistic adds out-of-sample ranking variance that **hurts AUC more often than it helps**, and L2 can shrink the junk coefficient but not to exactly zero without erasing signal too. On a high-accuracy classifier's correctness target, **junk reliably hurts**, so no positive null floor exists — independent of feature scaling.

This is broader than SST-2: it would recur on **any high-accuracy model's correctness target** (small minority class), suggesting the binding issue is the **target's class balance**, not this substrate specifically.

## Disposition — RETIRED (substrate ineligible; pivot to ChatGPT-detector)

**Resolution (2026-06-08, Option B):** the empirical noise-null screen was run across substrates — SST-2 P95 −0.086, Toxic-BERT −0.0006 (fails despite 277 errors), ChatGPT-detector RoBERTa **+0.026 (clears)**. SST-2 (and Toxic-BERT) are retired as ineligible; the program pivots to the ChatGPT-detector substrate. v2 is **never locked**. The criterion refinement (paper count necessary-not-sufficient; empirical noise-null P95>0 is the gating screen) is codified in `OVP_DESIGN_HISTORY.md`.

The script is built, compiles, both invariants hold, and the mirror is v1-faithful — **no implementation defect.** But the smoke predicts that **v2 as pinned will very likely return MIS-SPECIFIED via check 1**, for a reason standardization cannot fix. This is a design-level finding surfaced pre-lock (the build-and-smoke step's purpose), and it is a decision point, not a blocker to patch: see the chat decision (run v2 for the controlled-contrast record vs. pivot to a substrate/target with a substantial minority class vs. reconsider the floor rule). Caveat: the smoke is a non-canonical numpy mirror; the locked sklearn run under `0x55712` is the only citable answer, but the regularization sweep makes the structural read robust.
