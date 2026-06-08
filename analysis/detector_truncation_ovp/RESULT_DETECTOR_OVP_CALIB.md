# RESULT — DETECTOR_OVP_CALIB (cut-point calibration sub-study, ChatGPT-detector substrate)

**Study:** DETECTOR_OVP_CALIB — substrate-specific HDG cut-point calibration on the ChatGPT-detector RoBERTa confidence/correctness substrate, under the standardized-feature logistic (lock 1 of the two-lock arc for OVP's first *eligible* real candidate audit).
**Governing spec:** OVP v0.1 @ signed tag `ovp-v0.1-lock`.
**Lock:** signed tag `detector-ovp-calib-lock` (pre-reg + `calibrate_detector_cutpoints.py` + `materialization_manifest_detector_calib.json`; **two clean cold passes on byte-identical artifacts**).
**Execution:** single run, master seed `0xD37EC7`, `R_cal = 200`, 2026-06-08 UTC; outputs at signed tag `detector-ovp-calib-result`.
**Citation gate:** this result is citable only after its own cold cross-pass (spec §7); see `CROSSPASS_DETECTOR_OVP_CALIB.md`.

---

## Outcome: **USABLE BAND** — all three §6 separability checks pass

| §6 separability check | Result |
|---|---|
| 1. `τ_lo > 0` | **PASS** — `τ_lo = 0.024589` = `max(P95 redundant=0.000000, P95 noise=0.024589)` |
| 2. valid band, gap ≥ δ=0.01 | **PASS** — `τ_hi = 0.068291` (at σ_m=1.5), gap **0.043702** |
| 3. monotonicity + nulls ≤ ε_null | **PASS** — 8-point sweep monotone; null means `0.000000` (redundant), `+0.002368` (noise), both ≤ ε_null=0.01 |

**Decision band (frozen, on the AUC HDG scale):** **`[τ_lo = 0.024589, τ_hi = 0.068291]`**. A candidate's held-out discriminative gain `D` (ΔAUC from adding it to confidence) is judged: **`D < 0.024589` → Not-Validated**; **`0.024589 ≤ D ≤ 0.068291` → Inconclusive**; **`D > 0.068291` → Validated**.

### Milestone
This is **the first time the full OVP machinery has produced a usable decision band on real data**, under full discipline — canonical seed, single locked execution, two independent clean cold passes, and the disclosed `ε_null = δ` encoding correction. It is distinct from (and prior to) any verdict the lock-2 `truncated` candidate study will return. (Per the pre-committed milestone distinction in `OVP_DESIGN_HISTORY.md`: the build-and-smoke surfaced the design issues; *this locked run is the result*.)

## The numbers (all auditable from `detector_calibration_results.json` under the pinned numpy `'linear'` rule, unless sourced otherwise)

- Substrate: n = 2000, errors = 644, **accuracy 0.678** (`support`). Baseline `AUC(B→y)` median **0.5954** — confidence is only weakly predictive of the detector's own correctness, within the pre-registered ≈0.58–0.66 expectation. The weak baseline is *why* a candidate has room to add gain.
- **Noise null re-centered at zero** (the eligibility property): over 200 replications, median **+0.0059**, P5 **−0.0329**, **P95 +0.024589**, max +0.0354, **36% ≤ 0**. Mean **+0.002368** (inside ε_null). This is the substrate-instrument combination that makes a strictly-positive floor exist — contrast SST-2's noise null at mean −0.240 / P95 −0.086.
- Redundant null (`2B−1`): HDG **exactly 0.0 in all 200 replications** (`max|HDG| = 0`) — the pre-registered invariant 2 confirmed on the real run.
- Meaningful sweep (AUC P5 / mean): clears at σ_m ≤ 1.5 (P5 +0.299 / +0.141 / +0.068 for σ_m 0.5/1.0/1.5); does not clear at σ_m ≥ 2.0; **monotone** in σ_m (means 0.328 → 0.019). `τ_hi` = P5 at the weakest clearing point, σ_m=1.5 = 0.068291.
- Error-class AP panel (sensitivity, non-gating): nulls ≈ 0 (redundant +0.000, noise −0.005), meaningful positive & monotone (+0.446 at σ_m=0.5 → +0.010 at σ_m=4.0).
- Determinism cross-check vs the audit `predictions.csv`: **PASS**, max|Δ predicted_prob_ai| = 2.8e-06 (< 1e-5), 0 truncated mismatches.

## Why this substrate yielded a band (and SST-2 did not)

The difference is the **error-class size**, exactly as the substrate-eligibility criterion predicted. The detector is genuinely uncertain (67.8% accuracy → 644 errors, ~32% minority), so adding a pure-noise feature to the standardized logistic neither reliably helps nor reliably hurts held-out ranking — the noise null **centers at ~0** with a strictly-positive 95th percentile, giving `τ_lo = 0.0246 > 0`. On SST-2 (91% accurate, 78 errors) the same construction sat entirely below zero and no positive floor existed. The empirical noise-null screen that selected this substrate (P95 +0.026 pre-lock) is confirmed by the locked run (P95 +0.0246). The `ε_null = δ` correction was load-bearing: the noise null's locked mean is +0.0024 — positive, so the prior strict `≤ 1e-9` encoding would have returned a false MIS-SPECIFIED on the sign of sampling noise.

## What this establishes / does not

- **Does:** fix the ChatGPT-detector-specific HDG cut points `[0.024589, 0.068291]` under the pinned standardized estimator, sourced independently of any candidate; demonstrate end-to-end that the OVP machinery produces a usable band on an empirically-eligible real substrate.
- **Does not:** judge `truncated` or any candidate (never computed here); validate OVP in general; move the spec-§6 maturity ladder (this calibration yields no ledger verdict, as pre-registered); generalize beyond this substrate–instrument pairing.

## Frozen into lock 2

`τ_lo`, `τ_hi`, the supporting distributions, and the standardized estimator are frozen into `PRE_REGISTRATION_DETECTOR_TRUNCATION_OVP.md` (lock 2) before *its* lock. Lock 2 inherits the per-example materialization `detector_per_example.csv` (carrying `B`, `y`, **and `truncated`**) and judges whether **`truncated` adds held-out discriminative gain beyond the detector's confidence** in predicting detector correctness — OVP's first real ledger verdict. Lock 2 must pin the identical standardized estimator; `truncated`'s gain is judged against `[0.024589, 0.068291]`.

## Provenance

Dataset `chatgpt_detector_roberta_test_set.csv` sha256 `a29f8f2c…ff615a47` (verified unconditionally at run); model `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c61775d5dd0221808a79983ed3b86ffd86`, AI-class index 1, `max_length=512` (3-way identity enforced at lock); per-example materialization `detector_per_example.csv` sha256 `24dac078…01afc643` (durable file + results meta); estimator `StandardScaler(train-fit) → LogisticRegression(lbfgs, C=1.0, max_iter=1000, fit_intercept=True)`; seed `0xD37EC7` (= canonical), R_cal 200 (= canonical); environment per `materialization_manifest_detector_calib.json` (Python 3.12.10, numpy 2.1.2, scikit-learn 1.8.0, transformers 5.9.0, torch 2.12.0+cpu). Full per-replication HDG distributions (AUC + AP, 10 constructions × 200) persisted under `hdg_distributions` per the §7 persistence contract — every figure above is checkable from the frozen artifacts alone.
