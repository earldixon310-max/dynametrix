# Pre-Registration — DETECTOR_OVP_CALIB (cut-point calibration sub-study, ChatGPT-detector substrate)

**Study type:** Substrate-specific cut-point calibration study — the OVP §1 "bootstrap path" instantiated on **real data**. It is **lock 1 of the two-lock arc** for OVP's first *eligible* real candidate audit; it does **not** judge any real candidate.
**Governing spec:** OVP v0.1, locked at signed tag `ovp-v0.1-lock`. **Lock-status note:** OVP v0.1 was locked **tag-only / byte-exact** — the spec *body* retains its "working draft — not locked" line by design; the authoritative lock is carried by the signed tag, `OVP_v0.1_LOCK_NOTICE.md`, and `OVP_DESIGN_HISTORY.md` (verify via `git tag -v ovp-v0.1-lock`). This study conforms to the spec at that tag; the spec governs.
**Status:** DRAFT — not locked. (Review-progress is tracked outside this artifact, in `CROSSPASS_DETECTOR_OVP_CALIB.md`, not narrated here.)

---

## 0. Architectural framing (the two-lock arc) and what this study does NOT establish

OVP_POSCONTROL_v1 validated the decision rule **in a synthetic world**; per spec §1 a real candidate study needs its **own** externally-sourced cut points → a substrate-specific calibration. The SST-2 arc (v1 unstandardized, v2 standardized) established that a substrate's correctness target is **only eligible if its error class is large enough that junk features do not reliably hurt held-out ranking** (the documented v0.1 floor-rule limitation; see `OVP_DESIGN_HISTORY.md`). The SST-2 substrate failed that screen and was retired. **This study runs on a substrate that passed it.** Hence two locks:

```
OVP_POSCONTROL_v1               → proves the validator can ring true (done; PASS)
DETECTOR_OVP_CALIB (this study) → freezes ChatGPT-detector-specific τ_lo / τ_hi (standardized estimator)
DETECTOR_TRUNCATION_OVP (lock 2)→ judges whether `truncated` earns its existence beyond detector confidence
```

**The first execution of this audit is this calibration — not the truncation test.** This study answers: *what do null, redundant, and meaningful HDG distributions look like on the ChatGPT-detector confidence/correctness substrate under the standardized estimator?* Only once that is fixed can `truncated` be judged.

**This study does NOT:** judge `truncated` or any real candidate; validate OVP generally; establish anything about other detectors, domains, or descriptors; move the §6 maturity ladder. It only **sets the ruler** for one substrate–instrument pairing.

---

## 0.1 Why this substrate, and why the standardized estimator (both empirically grounded)

**Substrate eligibility (the decisive screen).** Per the codified substrate-eligibility criterion (`OVP_DESIGN_HISTORY.md`), a substrate is eligible only if the standardized **noise-null HDG distribution has P95 > 0** (a strictly-positive floor is achievable). Screening three locked audit substrates with that exact test settled the choice:

| Substrate | Accuracy | Errors (minority of correctness) | Standardized noise-null P95 | Eligible |
|---|---|---|---|---|
| DistilBERT-SST2 | 0.911 | 78 | −0.086 | no |
| Toxic-BERT | 0.945 | 277 | −0.0006 | no (fails despite ≥150 errors) |
| **ChatGPT-detector RoBERTa** | **0.678** | **644** (balanced labels) | **+0.026** | **yes** |

The ChatGPT-detector substrate clears the floor (noise-null P95 +0.026; strongest meaningful arm P5 ≈ +0.30 far above) because the model is **genuinely uncertain** (67.8% accuracy → a large, ~32% error class), so adding an irrelevant feature does not reliably destroy held-out ranking. This is the screen's gating output, computed pre-lock with the same estimator below; the locked run is the definitive, citable version.

**Estimator (standardized).** The estimator is the **standardized-feature logistic** validated as the working instantiation in the SST-2 v2 diagnostic (`StandardScaler` fit on train → L2 logistic). The cut points this study produces are valid **only** for this instantiation, and lock 2 must use the identical estimator.

---

## 1. Objective

Produce externally-sourced decision cut points (`τ_lo`, `τ_hi`) on the **ChatGPT-detector confidence/correctness HDG scale under the standardized-feature logistic**, before the `truncated` candidate study, by measuring what HDG known-null vs known-meaningful constructions produce on this real substrate — never from the candidate study's own run.

---

## 2. Substrate and materialization

- **Model (pinned):** `Hello-SimpleAI/chatgpt-detector-roberta` at revision **`d2b342c61775d5dd0221808a79983ed3b86ffd86`** (the ChatGPT-detector audit revision; `id2label = {0: Human, 1: ChatGPT}`, **AI-class index = 1**). Deterministic inference (no sampling).
- **Dataset (pinned):** the audit's materialized RAID test subsample `case_studies/chatgpt_detector_roberta_v1/chatgpt_detector_roberta_test_set.csv` (2000 examples; columns `id, text, is_ai_generated, source_domain, source_model`), sha256 **`a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47`** (RAID dataset revision `865cac74…`).
- **Per-example materialization (produced here; inherited by lock 2):** run the pinned model once over the 2000 texts (`max_length = 512`, `truncation=True`, `padding=False`) to produce, per example: `predicted_prob_ai = softmax(logits)[1]`; predicted label `pred = 1[ predicted_prob_ai ≥ 0.5 ]`; **`B = confidence = max(predicted_prob_ai, 1 − predicted_prob_ai)`**; **`y = correctness = 1[ pred == is_ai_generated ]`**; and **`truncated = 1[ len(tokenizer(text, truncation=False).input_ids) > 512 ]`** (the lock-2 candidate, computed and stored here but **not used in this calibration**). Written to `detector_per_example.csv` with a SHA-256 persisted durably (`detector_per_example_sha256.txt`, also in the results meta — never stdout-only). The calibration uses only `B`, `y`, and the substrate size. **Determinism cross-check:** the materialized `(predicted_prob_ai, truncated)` are expected to reproduce the audit's `predictions.csv` (deterministic inference); a mismatch aborts.
- **Substrate profile (context):** n = 2000, accuracy ≈ 0.678, errors ≈ 644 (the y=0 class), labels balanced (~1000/1000). Confidence is still right-skewed (median ≈ 0.994) but the large error class is what makes the floor achievable (§0.1).

---

## 3. HDG instantiation (pinned)

- **Primary discrimination metric:** ROC **AUC** on a held-out split — pinned for consistency with OVP_POSCONTROL_v1 and the SST-2 studies.
- **Sensitivity panel (reported, not gating):** **average precision (AP)**, computed with **error as the positive class** — relabel `1 − y` (so `1` = error) and score predicted error probability `1 − P(correct)`. (AUC is class-symmetric; AP is the imbalance-robustness check. Here the error class is ~32%, so AP is well-defined and informative.) Computed from the same standardized-estimator predictions; does **not** set the cut points.
- **Estimator / function class (pinned):** an sklearn `Pipeline` of **`StandardScaler(with_mean=True, with_std=True)` → `LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)`** (L2), **`fit` on the training partition only.** Concretely: the scaler's per-feature mean/std are estimated from the **train** rows (`fit` → `transform` on train), and the **held-out** rows are then scaled using **those train-fit statistics** (`transform` on test) before scoring; the held-out rows never influence the scaler — **no test-set leakage.** Identical to the SST-2 v2 instantiation; lock 2 must reuse it exactly.
- **`D = AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`** on the held-out test split.
- **Resampling scheme:** because the dataset is **fixed** (2000 examples), "replications" are **repeated stratified 50/50 train/test splits** of the same 2000, stratified on `y` (correctness). This is the **single resampling scheme** (no bootstrap; the partition-variance estimand is the target, not the broader-population estimand).
- **Replications:** `R_cal = 200` stratified splits per construction. **Master seed `0xD37EC7`** — a **fresh seed**, distinct from all prior studies (SST-2 used `0x55712`; the positive control used `0xFACADE`/`0xCA11B`) and distinct from lock 2's seed. Seed derivation: NumPy `SeedSequence(master).spawn(R_cal)`, one child per replication in index order; within a replication each construction draws its noise then its own split seed from the advancing child stream (constructions **not** split-paired within a replication; sound because the cut-point rules use each construction's **marginal** HDG distribution only).

**Two pre-registered invariants** (the build-and-smoke and the run confirm the standardization behaves correctly):
1. **Baseline-AUC invariance / level.** For the single-feature baseline `pipeline[B]`, standardizing one feature is a monotone transform, so the held-out ranking and `AUC_test(pipeline[B])` are unaffected by standardization; the baseline `AUC(B→y)` median is expected ≈ **0.58–0.66** on this substrate (a genuinely-uncertain detector; confidence is only weakly predictive of its own correctness — the smoke estimate was ≈0.60).
2. **Redundant-null exact zero.** `C = 2B−1` is affine in `B`; after per-column z-scoring the two standardized columns are identical, so `pipeline[B, 2B−1]` ranks identically to `pipeline[B]` → **HDG = 0 in every replication** (exactly, up to logistic optimizer numerics — far inside the check-3 `ε_null` tolerance, which it satisfies trivially). Hence `τ_lo` is governed entirely by the **noise** null's P95 (which the §0.1 screen showed is strictly positive on this substrate).

---

## 4. Calibration constructions (synthetic candidates on the real substrate)

Computed on the real `(B, y)` per-example data; identical forms to the prior calibrations:

- **Null-redundant:** `C = 2·B − 1` (deterministic affine of confidence) — HDG ≡ 0 (§3 invariant 2).
- **Null-noise:** `C = Normal(0,1)` per example, independent of everything. On this substrate, expected to re-center near 0 with a strictly-positive P95 (§0.1).
- **Meaningful sweep:** `C = y + Normal(0, σ_m²)` — a noisy copy of the correctness target, carrying genuine correctness signal beyond `B`. Swept over `σ_m` on the pinned grid **{0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}** (uniform 0.5 spacing; larger `σ_m` = weaker). (`y + noise` leaks the target *by design* to establish what a meaningful gain looks like; never used in the candidate study.)

Each construction / grid point is evaluated over `R_cal = 200` stratified splits.

---

## 5. Cut-point rules (pinned here; values produced by the run)

All percentiles use numpy default `'linear'` (type-7) interpolation (result-affecting; fixed).

- **`τ_lo` = `max( P95(HDG | null-redundant), P95(HDG | null-noise) )`** — the higher of the two nulls' 95th percentiles. Must be strictly positive.
- **`τ_hi`** — from the meaningful sweep, by the three-step rule: **(1)** identify sweep points whose `P5(HDG) > τ_lo + δ` (margin `δ = 0.01` AUC); **(2)** among those, choose the **largest `σ_m`** (weakest meaningful signal that still clears); **(3)** set `τ_hi =` that point's `P5(HDG)`. Grid-resolution limitation (0.5 quantum) documented as in the prior calibrations.

(No arm-placement parameters are frozen here; the lock-2 candidate study judges a single real candidate, so only `τ_lo` and `τ_hi` are produced.)

---

## 6. Separability check / mis-specification exit (a pre-committed outcome, not a failure)

After the run, **all** must hold; otherwise the design is declared **MIS-SPECIFIED** and revised under a **new** lock, never fudged into a band:

1. `τ_lo > 0`.
2. `τ_lo < τ_hi` with a gap `≥ δ = 0.01` AUC — **a valid band exists.**
3. Monotonicity: mean HDG on the meaningful sweep increases **non-strictly** (`≤` between adjacent points, weakest→strongest) as `σ_m` decreases, over 8 points; both nulls have mean HDG **`≤ ε_null = δ = 0.01`** — a **one-sided tolerance** encoding the "≤ ~0" intent: a genuine null must not *average* a gain reaching the decision margin. One-sided, so a legitimately-negative null (junk that *hurts*, as on the rejected high-accuracy substrates) still passes; the tolerance reuses the pinned `δ` rather than a freely-chosen number. *(The strict `≤ 1e-9` encoding used in the SST-2 calibrations was a transcription of the "≤ ~0" intent that becomes a sampling-noise knife-edge on any **eligible** substrate — where the null centers at ~0 by construction, so its sample mean's sign is noise. Corrected here; the general encoding lesson is recorded in `OVP_DESIGN_HISTORY.md`.)*

**Expectation vs the pre-committed exit.** Unlike SST-2, this substrate **passed the empirical eligibility screen** (noise-null P95 +0.026 > 0), so a valid band is **expected**. The MIS-SPECIFIED exit remains pre-committed and live — the locked run under the canonical seed is the definitive test and could still fail (e.g., the strong meaningful arm overlaps a wider-than-screened null, or monotonicity breaks) — but a MIS-SPECIFIED here would be **surprising and itself informative** (it would mean the screen, run pre-lock at a non-canonical seed, did not transfer), not the expected outcome. If MIS-SPECIFIED, the truncation study does not proceed and the finding is published; options are a different estimator/metric instantiation or another eligible substrate, each a new pre-registration.

---

## 7. Outputs frozen into the candidate study

**Persistence contract:** under single-execution discipline, anything the one locked run does not persist is unrecoverable without a forbidden re-run — so the run writes **everything needed to audit it**, and **nothing beyond this pinned set**.

**Pinned output set, written to `detector_calibration_results.json`:**

- `τ_lo`, `τ_hi`, and the `σ_m` at `τ_hi`;
- the **full per-replication HDG arrays** — all `R_cal` values per construction, **AUC and AP** — under `hdg_distributions` (keys: `null_redundant`, `null_noise`, `meaningful:<σ_m>`);
- summary support: the null P95s; the **null means** (§6-check-3 inputs); the meaningful-sweep P5s and means; the AP sensitivity-panel means; `baseline_auc_median_nullnoise_splits` (construction-independent baseline `AUC(B→y)` median over null-noise splits; context diagnostic, not gating); `n_examples`; `n_errors`;
- the §6 separability-check booleans and the verdict string;
- meta: canonical and used seed, canonical and used replication count, `δ`, model id + revision, dataset sha256, the per-example CSV SHA-256, the estimator descriptor, and a UTC timestamp.

**Durable materialization records:** `detector_per_example.csv` (carrying `B`, `y`, **and `truncated`** for lock-2 inheritance) plus `detector_per_example_sha256.txt`; the hash is also recorded in the results meta.

If a valid band exists: `τ_lo`, `τ_hi` (with the supporting distributions) are frozen into `PRE_REGISTRATION_DETECTOR_TRUNCATION_OVP.md` (lock 2) before *its* lock, **and lock 2 must pin the identical standardized estimator**. The per-example materialization (incl. `truncated`) is inherited by lock 2 (the candidate study reuses the same `B`, `y` and judges `truncated`).

---

## 8. Materialization, lock, execution (ordered steps)

1. **Build-and-smoke** `calibrate_detector_cutpoints.py` strictly to this pre-reg; smoke on a non-canonical seed (real `(B, y)` if available, else simulated), confirming the two §3 invariants and that the nulls re-center; then the pre-cold-pass **spec↔implementation output-conformance check** (`OVP_DESIGN_HISTORY.md`).
2. **Cross-pass:** warm review, then **two independent cold passes**, ≥1 cold, fix-author cannot clear. Recorded in `CROSSPASS_DETECTOR_OVP_CALIB.md`.
3. **Lock** (`detector-ovp-calib-lock`): this pre-reg + `calibrate_detector_cutpoints.py` (which materializes `detector_per_example.csv` from the pinned model) + `materialization_manifest_detector_calib.json` (generator aborts on dataset-hash or model-revision-identity mismatch), one atomic commit + signed tag.
4. **Run exactly once** (no flags) → materialize per-example `(B, y, truncated)`; produce `τ_lo`, `τ_hi`, the HDG distributions (AUC + AP), the §6 result — persisting exactly the §7 set.
5. **Freeze** outputs into lock 2 (or, if MIS-SPECIFIED, publish that finding and stop).

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run. The outcome is recorded regardless of whether a band emerges.

---

## 9. What this establishes / does not (restated)

- **Does:** fix the ChatGPT-detector-specific HDG cut points under the standardized-feature logistic (or honestly report MIS-SPECIFIED), sourced independently of the candidate run, on an empirically-eligible substrate.
- **Does not:** judge `truncated`; validate OVP; move the §6 ladder; generalize beyond this substrate–instrument pairing.

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; the fix-author (including the AI collaborator) cannot be a clearing reader. A warm pass against the pinned pre-commitments precedes the cold passes. The pre-cold-pass build-and-smoke + output-conformance check is a precondition. Recorded in `CROSSPASS_DETECTOR_OVP_CALIB.md`.

---

## 11. Discretionary pins (pinned as written; for explicit pre-lock sign-off)

1. Primary metric AUC; sensitivity panel AP on the **error class** (relabel `1 − y`, score `1 − P(correct)`), from the standardized-estimator predictions.
2. Resampling: repeated stratified 50/50 splits — the single scheme; **no bootstrap** (partition-variance estimand).
3. `R_cal = 200`; full 2000 examples re-split each replication.
4. Meaningful sweep `σ_m` grid {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}; null forms (`2B−1`, `N(0,1)`); percentile rule (max-of-95ths `τ_lo`, P5-of-weakest-clearing `τ_hi`); margin `δ = 0.01`; check-3 null-mean tolerance `ε_null = δ = 0.01` (one-sided).
5. **Estimator: `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, solver='lbfgs'))`, fit on the training partition only.**
6. **Seed `0xD37EC7`** (fresh; distinct from all prior studies and from lock 2); numpy `'linear'` percentile interpolation.
7. Substrate: model `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c6…`, AI-class index 1, `max_length=512`; dataset `chatgpt_detector_roberta_test_set.csv` sha `a29f8f2c…`; per-example materialized fresh here (B, y, truncated), with a determinism cross-check against the audit's `predictions.csv`.

*End of draft pre-registration. Awaiting build-and-smoke + warm pass + two cold passes; not locked.*

---

## 12. Relationship to the SST-2 arc and to lock 2

The SST-2 arc (retired, MIS-SPECIFIED at calibration under both estimators) produced the substrate-eligibility criterion this study's substrate was selected by; that is the methodological link, not a dependency. This calibration is a fresh, independent study. If it yields a band, lock 2 (`DETECTOR_TRUNCATION_OVP`) inherits these cut points, this standardized estimator, and the materialized `(B, y, truncated)`, and judges whether **`truncated` adds held-out discriminative gain beyond the detector's own confidence** in predicting detector correctness — OVP's first real ledger verdict, on a substrate chosen because it can actually support one.
