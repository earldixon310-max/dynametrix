# Script-build findings — calibrate_detector_cutpoints.py vs the DETECTOR_OVP_CALIB pre-reg

Build-and-smoke precondition (`OVP_DESIGN_HISTORY.md`): script built strictly to the pre-reg, then smoke-tested on a non-canonical seed **before** cold-pass routing. The smoke ran the calibration logic mirror (numpy-only IRLS logistic + train-fit z-scoring, error-class AP) on the **real `(B, y)`** read from the audit's `predictions.csv` — the first smoke on a substrate that passed the empirical eligibility screen.

## Build conformance

`calibrate_detector_cutpoints.py` compiles clean. Pins verified against the pre-reg (and against SST-2 v2's earned values): AP error-class relabel, σ_m grid {0.5…4.0}, R_cal=200, numpy `'linear'`, stratified 50/50, L2 logistic C=1.0/lbfgs, train-fit `StandardScaler` pipeline, δ=0.01, fresh seed `0xD37EC7`. Materialization re-runs the pinned RoBERTa (id `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c6…`, AI-class idx 1, max_len 512) over the hashed RAID test set, computes `truncated` (full-token-len > 512) for lock-2 inheritance, and cross-checks `(predicted_prob_ai, truncated)` against the audit `predictions.csv` (abort on mismatch).

## Smoke results (real (B,y), non-canonical seed 0xBEEF)

Substrate: n=2000, accuracy 0.678, errors 644, B median 0.994.

- **Invariant 2 (redundant null ≡ 0):** `max|HDG| = 0.00e+00`. ✓
- **Invariant 1 (baseline AUC level):** median **0.597** — slightly **below** the pre-reg's stated ≈0.62–0.66. Minor; confidence is even *less* predictive of correctness than estimated (more room for a candidate). **Fix:** widen §3 invariant-1 expectation to ≈ **0.58–0.66**. Non-gating (descriptive, not a §6 check).
- **Noise null:** mean **+0.0027**, P5 −0.029, **P95 +0.025**, 37% ≤ 0 — **re-centered at zero** (vs SST-2's −0.24). `τ_lo = max(0.0, +0.025) = +0.025 > 0`. The floor is positive — the substrate is eligible, as screened.
- **Meaningful sweep** clears at σ_m ≤ 1.5 (P5 +0.069 at σ_m=1.5), monotone over 8 points; AP error-class panel positive & decreasing (+0.45 → +0.01), nulls ≈ 0.
- **Provisional band (AUC):** `[τ_lo≈0.025, τ_hi≈0.069]` at σ_m=1.5 — a real band on real data.

## FINDING (design, gating) — check 3's null-mean condition is mis-encoded for eligible substrates

The script encodes check 3's "both nulls have mean HDG ≤ ~0" (pre-reg §6.3) as `null_mean ≤ 1e-9` (strictly ≤ 0). On SST-2 the noise null sat at −0.24, so this passed trivially. On an **eligible** substrate the noise null is centered at ~0 *by construction* (that is what makes `τ_lo > 0` possible), so its 200-rep **sample mean is a near-zero number whose sign is sampling noise** (+0.0027 here; could be −0.0027 under a different seed). The strict `≤ 1e-9` bound therefore makes the verdict **hinge on the sign of sampling noise** — an unacceptable gate property, and a spec↔implementation divergence: §6.3 says "≤ ~0" (*approximately*), the code says strictly ≤ 0.

**This means the current bytes would return MIS-SPECIFIED via check 3** on a substrate that is otherwise cleanly separable — a false negative driven by the encoding, not the data.

**Proposed fix (operator decision):** replace the strict bound with a small **one-sided** tolerance matching the stated intent — both null means `≤ ε_null`, with **`ε_null = δ = 0.01`** (a genuine null must not average a gain reaching the decision margin). Rationale: cleanly separates nulls (+0.0027, 0.0) from meaningful arms (+0.02…+0.33); passes SST-2's −0.24; one-sided so a negative null (junk hurts) still passes; reuses an existing pinned constant rather than a fitted number. This touches a §6 gate, so it is a pre-cold-pass design decision, and the lesson generalizes — the check should be corrected in the OVP discipline record as well (the strict encoding is latent-buggy for any eligible substrate, independent of this one).

## Fix applied + clean re-smoke (2026-06-08, operator-approved)

Both refinements applied: (1) invariant-1 expectation widened to ≈0.58–0.66 (§3); (2) **check-3 null-mean tolerance corrected to `ε_null = δ = 0.01` (one-sided)** — pre-reg §6.3 + §11.4 and the script's `EPS_NULL` constant + `nulls_nonpos` line. The generic encoding lesson (approximation qualifiers `≈`/`~` must be encoded as explicit tolerances, preferring a pinned constant) is recorded in `OVP_DESIGN_HISTORY.md`, with the milestone distinction (smoke surfaces; the locked run is the result).

**Re-smoke under the corrected gate (real (B,y), seed 0xBEEF):** all three checks pass cleanly — null means redundant +0.00000 / noise +0.00274 (both ≤ ε_null=0.01); check 1 `τ_lo=0.0251>0`; check 2 band gap 0.0435 ≥ δ; check 3 monotone ∧ nulls ≤ ε. **SEPARABLE = True, USABLE BAND [0.0251, 0.0686] at σ_m=1.5.** The corrected gate accepts the zero-centered null without hinging on its sign.

**Note — sandbox mount artifact:** the sandbox bash mount serves a 13-line-truncated copy of the edited script (a known file-tool/mount lag), so `py_compile` via bash spuriously reports an unterminated string at the tail. The file-tool view (= the authoritative on-disk file) is complete and well-formed through line 257 (the `meta` dict closes; `main()` intact); the edits are clean. Definitive compile to be confirmed by the operator locally (`python -m py_compile`) before cross-pass routing.

## Disposition

Script built, invariant 2 exact, materialization + cross-check sound, **corrected check-3 gate now yields a clean USABLE BAND on real data in the smoke** — no implementation defect in the calibration mechanics. Ready (pending the operator's local `py_compile` confirmation) for the pre-cold-pass output-conformance check, then the warm pass + two cold passes on the corrected bytes. The numpy-mirror band is directional only; the locked sklearn run under `0xD37EC7` is the definitive, citable result and the milestone trigger.
