# Pre-Registration — SST2_OVP_CALIB_v2 (cut-point calibration sub-study, standardized-feature instantiation)

**Study type:** Substrate-specific cut-point calibration study — the OVP §1 "bootstrap path" instantiated on **real data**. It is **lock 1 of the two-lock arc** for OVP's first real candidate audit; it does **not** judge any real candidate. This is a **new pre-registration and a new lock**; it does not modify, re-run, or supersede SST2_OVP_CALIB (v1), which remains the locked record of the unstandardized-estimator finding.
**Governing spec:** OVP v0.1, locked at signed tag `ovp-v0.1-lock`. **Lock-status note:** OVP v0.1 was locked **tag-only / byte-exact** — the spec *body* retains its "working draft — not locked" line by design; the authoritative lock is carried by the signed tag, `OVP_v0.1_LOCK_NOTICE.md`, and `OVP_DESIGN_HISTORY.md` (verify via `git tag -v ovp-v0.1-lock`). This study conforms to the spec at that tag; the spec governs.
**Status:** **RETIRED — never locked.** The build-and-smoke (on the real `(B, y)`, validated against v1's locked noise null + a regularization sweep) established that the SST-2 correctness substrate is **ineligible** under the empirical noise-null screen: standardization helps but the noise null stays below zero, so `τ_lo > 0` cannot hold — a structural consequence of the tiny error class, not a tunable defect. Per the Option-B decision (2026-06-08), the program retired the SST-2 substrate rather than lock v2 to a near-certain MIS-SPECIFIED, and pivoted to an empirically-eligible substrate (ChatGPT-detector RoBERTa). This pre-reg and `calibrate_sst2_cutpoints_v2.py` are kept as the record of the standardized-estimator diagnostic; see `OVP_DESIGN_HISTORY.md` (documented limitation + substrate-eligibility criterion + empirical-screen refinement) and `SCRIPT_BUILD_FINDINGS_SST2_CALIB_v2.md`.

---

## 0. Architectural framing (the two-lock arc) and what this study does NOT establish

OVP_POSCONTROL_v1 validated the decision rule **in a synthetic world**. It did **not** create universal cut points: HDG (ΔAUC) is scaled by the substrate's target distribution, feature geometry, and sample size, so the positive control's `τ_lo`/`τ_hi` do not transfer to real data. Per spec §1, a real candidate study needs its **own** externally-sourced cut points → a substrate-specific calibration. Hence two locks:

```
OVP_POSCONTROL_v1               → proves the validator can ring true (done; PASS)
SST2_OVP_CALIB_v2 (this study)  → freezes SST-2-specific τ_lo / τ_hi under a standardized estimator
SST2_NEGATION_OVP (lock 2)      → judges whether negation_count earns its existence beyond confidence
```

**The first execution of OVP's first real audit is this calibration — not the negation test.** This study answers: *what do null, redundant, and meaningful HDG distributions look like on the SST-2 confidence/correctness substrate under a standardized-feature logistic?* Only once that is fixed can negation be judged.

**This study does NOT:** judge negation or any real candidate; validate OVP generally; establish anything about weather, descriptors, or any other domain; move the §6 maturity ladder. It only **sets the ruler** for one substrate–instrument pairing. A v0.x reader should not read more into it.

---

## 0.1 What changed from v1, and why (the single pin)

SST2_OVP_CALIB (v1) ran once under seed `0x55712` and returned **MIS-SPECIFIED via §6 check 1** (`τ_lo = 0.0`; strict positivity failed). The cleared result document (`RESULT_SST2_OVP_CALIB.md`, citation gate met) and the frozen `sst2_calibration_results.json` establish the mechanism:

- DistilBERT-SST2 confidence `B` is **extremely compressed** (median 0.9995; 84.4% above 0.99).
- Under v1's **unstandardized** L2 logistic, `B` needs a very large coefficient to express its tiny dynamic range, while an `N(0,1)` junk feature needs almost none — so any nonzero weight on a junk feature scrambles the compressed ranking out-of-sample. The noise null was therefore **negative in 200/200 replications** (mean −0.240), and `max`-of-95ths returned exactly 0, failing check 1.

**The single pinned change in v2:** the HDG estimator standardizes features (z-score) **with scaler parameters fit on the training partition only**, before the logistic. This directly targets the mechanism: a standardized junk feature competes on equal footing with standardized `B`, so the L2 penalty shrinks its coefficient toward zero and the null HDG distribution should re-center near 0 (a symmetric upper tail, hence a strictly-positive `τ_lo`), instead of sitting entirely below zero. **Everything else is held identical to v1** — same dataset, same model revision, same per-example `(B, y)`, same AUC primary / error-class AP panel, same stratified-split scheme, same `R_cal`, same `σ_m` grid, same cut-point rules, same mis-specification exit, same persistence contract, **and (see §3) the same master seed**, so v1→v2 is a controlled one-variable contrast.

This is a "wrong-pin" hypothesis test. If v2 produces a valid band, the lesson is that the unstandardized pin (inherited from the scale-controlled positive control) interacts badly with real compressed confidence scales. If v2 **also** returns MIS-SPECIFIED, the lesson escalates from "wrong pin" toward "this substrate/metric pairing does not admit a clean ruler" — see §6.

---

## 1. Objective

Produce externally-sourced decision cut points (`τ_lo`, `τ_hi`) on the **SST-2 confidence/correctness HDG scale under a standardized-feature logistic**, before the negation candidate study, by measuring what HDG known-null vs known-meaningful constructions produce on this real substrate — never from the candidate study's own run.

---

## 2. Substrate and materialization (inherited from the v1 lock; not re-run)

- **Dataset (pinned):** `case_studies/distilbert_sst2/sst2_validation.csv` (872 examples; columns `idx, sentence, label`), sha256 `a0b4a680…2588376d` per `sst2_validation_sha256.txt`.
- **Model (pinned):** DistilBERT-SST2 @ revision `714eb0fa89d2f80546fda750413ed43d93601a13` (the DistilBERT-SST2 audit revision; deterministic inference).
- **Per-example `(B, y)` — inherited, not re-materialized.** Because the standardization change lives entirely inside the HDG *estimator*, the per-example confidence `B` and correctness `y` are **identical** to v1's. v2 therefore **reads the locked, cold-passed `sst2_per_example.csv` from the v1 lock** (tag `sst2-ovp-calib-lock`) and **verifies its sha256 against `sst2_per_example_sha256.txt` (`e9e5b12a…b7bec1c7`), aborting on mismatch** — rather than re-running the model. This makes v2 self-contained against the frozen substrate, removes any re-materialization nondeterminism, and means v1 and v2 operate on byte-identical `(B, y)`. `negation_count` is **not** computed here (it is the lock-2 candidate); the calibration uses only `B`, `y`, and the substrate size.

Note: `y` is imbalanced (78 errors in 872; accuracy 0.911). This is the central reason calibration must be substrate-specific; see §6/§7.

---

## 3. HDG instantiation (pinned)

- **Primary discrimination metric:** ROC **AUC** on a held-out split — pinned for **consistency with OVP_POSCONTROL_v1 and SST2_OVP_CALIB v1**, so verdict interpretation matches across studies.
- **Sensitivity panel (reported, not gating):** **average precision (AP)**, computed with **error as the positive class** — relabel `1 − y` (so `1` = error) and score predicted error probability `1 − P(correct)`, i.e. AP for *detecting errors*. (AUC, being class-symmetric, is unaffected by the relabel; AP is the imbalance-robustness check.) AP is reported alongside every HDG figure; it does **not** set the cut points. Computed from the **same standardized-estimator predictions** as the AUC figures.
- **Estimator / function class — THE v2 PIN CHANGE:** an sklearn `Pipeline` of **`StandardScaler(with_mean=True, with_std=True)` → `LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True)`**, L2 penalty (sklearn default). The pipeline is **`fit` on the training partition only**, so the scaler's per-feature mean and standard deviation are estimated from train data and then applied to **both** the train and the held-out test partitions — **no test-set leakage**. All logistic hyper-parameters are identical to v1; the *only* difference from v1 is the inserted, train-fit `StandardScaler`. (v1 was the same logistic on unstandardized features.)
- **`D = AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`** on the held-out test split, where each pipeline standardizes its own feature columns using train-fit statistics.
- **Resampling scheme:** because the dataset is **fixed** (872 examples), "replications" are **repeated stratified 50/50 train/test splits** of the same 872, stratified on `y`. This is the **single resampling scheme** (no bootstrap is run; the partition-variance estimand — "how stable is the candidate's incremental gain across train/test partitions of these 872 examples" — is the target, not the broader-population estimand). Identical to v1.
- **Replications:** `R_cal = 200` stratified splits per construction. **Master seed `0x55712` — deliberately the same as v1** (see §3 rationale below and §11). Seed derivation: NumPy `SeedSequence(master).spawn(R_cal)`, one child per replication in index order; within a replication each construction draws its noise then its own split seed from the advancing child stream (constructions **not** split-paired within a replication; each still receives `R_cal` valid master-seed-determined stratified splits; sound because the cut-point rules use each construction's **marginal** HDG distribution only).

**Why the same master seed (a deliberate, justified choice, not seed-reuse by oversight):** holding the seed fixed makes the train/test partitions and the synthetic-construction noise draws **byte-identical** to v1, so v1→v2 is a **controlled one-variable contrast** — every difference in the HDG distributions is attributable solely to the standardization pin. This is *not* seed-shopping: v1 already ran once to a fixed, published MIS-SPECIFIED outcome, so no degree of freedom is being exploited to favor a v2 result; the seed is held constant precisely to isolate the estimator change. (If at §11 sign-off a fresh seed is preferred instead, that is a one-line change; the controlled-contrast value would be forgone.)

**Two pre-registered invariants** (stated so the build-and-smoke and the run can confirm the standardization behaves as intended):
1. **Baseline-AUC invariance.** For the single-feature baseline `pipeline[B]`, standardization is a monotone affine transform of `B`, so the held-out ranking — and therefore `AUC_test(pipeline[B])` — is **unchanged** from v1. The baseline `AUC(B→y)` median is expected to remain ≈ **0.86**.
2. **Redundant-null exact zero.** `C = 2B−1` is affine in `B`; after per-column z-scoring, `std(2B−1) = std(B)` exactly (both increasing in `B`), so `pipeline[B, 2B−1]` has two identical standardized columns and ranks test points identically to `pipeline[B]` → **HDG ≡ 0 in every replication**, exactly as in v1. (Under `max`-of-95ths this means `τ_lo` is governed entirely by the **noise** null's P95; the open question v2 tests is whether standardization lifts that P95 strictly above 0.)

---

## 4. Calibration constructions (synthetic candidates on the real substrate)

Computed on the real `(B, y)` per-example data; identical forms to v1 / OVP_POSCONTROL_v1:

- **Null-redundant:** `C = 2·B − 1` (deterministic affine of confidence) — HDG ≡ 0 (see §3 invariant 2).
- **Null-noise:** `C = Normal(0,1)` per example, independent of everything. HDG ≈ 0 *if* standardization works as hypothesized (v1: strictly negative).
- **Meaningful sweep:** `C = y + Normal(0, σ_m²)` — a noisy copy of the correctness target, carrying genuine correctness signal beyond `B`. Swept over `σ_m` on the pinned grid **{0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}** (uniform 0.5 spacing; larger `σ_m` = weaker). (`y + noise` leaks the target *by design* to establish what a meaningful gain looks like; never used in the candidate study.)

Each construction / grid point is evaluated over `R_cal = 200` stratified splits.

---

## 5. Cut-point rules (pinned here; values produced by the run) — identical to v1

All percentiles use numpy default `'linear'` (type-7) interpolation (result-affecting; fixed).

- **`τ_lo` = `max( P95(HDG | null-redundant), P95(HDG | null-noise) )`** — the higher of the two nulls' 95th percentiles. Must be strictly positive.
- **`τ_hi`** — from the meaningful sweep, by the explicit three-step rule: **(1)** identify sweep points whose `P5(HDG) > τ_lo + δ` (margin `δ = 0.01` AUC); **(2)** among those, choose the **largest `σ_m`** (weakest meaningful signal that still clears); **(3)** set `τ_hi =` that point's `P5(HDG)`. Grid-resolution limitation (0.5 quantum) documented as in v1.

(No arm-placement parameters are frozen here; the lock-2 candidate study judges a single real candidate, so only `τ_lo` and `τ_hi` are produced.)

---

## 6. Separability check / **mis-specification exit (a pre-committed outcome, not a failure)**

After the run, **all** must hold; otherwise the design is declared **MIS-SPECIFIED** and documented + revised under a **new** lock, never fudged into a band:

1. `τ_lo > 0`.
2. `τ_lo < τ_hi` with a gap `≥ δ = 0.01` AUC — **a valid band exists.**
3. Monotonicity: mean HDG on the meaningful sweep increases **non-strictly** (`≤` between adjacent points, weakest→strongest) as `σ_m` decreases, over 8 sweep points; both nulls have mean HDG `≤ ~0`, encoded as `mean ≤ 1e-9`.

**Pre-committed possibilities (named in advance, informed by v1):**
- **The targeted fix succeeds:** standardization re-centers the noise null around 0, its P95 is strictly positive, `τ_lo > 0`, and a band `[τ_lo, τ_hi]` opens. The cut points freeze into lock 2 and the negation study proceeds.
- **Check 1 still fails (`τ_lo ≤ 0`):** standardization did not lift the noise null's P95 above 0 — the compressed-confidence substrate resists a strictly-positive floor even with equal-footing features. **MIS-SPECIFIED.**
- **Check 2 fails (band collapse, `τ_lo ≥ τ_hi`):** standardization widens the null distribution enough that its upper tail overlaps the weakest meaningful signal — the imbalance-driven failure mode v1 originally anticipated but did not exhibit. **MIS-SPECIFIED.**

A MIS-SPECIFIED outcome here is **the discipline working, not a failure**: combined with v1, two distinct estimator instantiations failing on the same substrate would be evidence that **the SST-2 confidence/correctness substrate (at this `N`, under logistic HDG) does not support a clean ruler** — a statement about the substrate–instrument pairing, not about negation (never reached). Continuation options (each a new pre-registration): a larger / lower-accuracy substrate with more errors (e.g., the Toxic-BERT audit data), a different feature transform (rank/logit of `B`), an AP-primary instantiation, or abandoning this substrate. The negation candidate study does not proceed unless a valid band exists.

---

## 7. Outputs frozen into the candidate study

**Persistence contract:** under single-execution discipline, anything the one locked run does not persist is unrecoverable without a forbidden re-run — so the run writes **everything needed to audit it**, and **nothing beyond this pinned set**.

**Pinned output set, written to `sst2_calibration_v2_results.json`:**

- `τ_lo`, `τ_hi`, and the `σ_m` at `τ_hi`;
- the **full per-replication HDG arrays** — all `R_cal` values per construction, **AUC and AP** — under `hdg_distributions` (keys: `null_redundant`, `null_noise`, `meaningful:<σ_m>`);
- summary support: the null P95s; the **null means** (§6-check-3 inputs); the meaningful-sweep P5s and means; the AP sensitivity-panel means; `baseline_auc_median_nullnoise_splits` (the construction-independent baseline `AUC(B→y)` median, sampled over null-noise splits; a context diagnostic, not gating); `n_examples`; `n_errors`;
- the §6 separability-check booleans and the verdict string;
- meta: canonical and used seed, canonical and used replication count, `δ`, model id + revision, the inherited per-example CSV SHA-256, the estimator descriptor (`"StandardScaler(train-fit) -> LogisticRegression(...)"`), and a UTC timestamp.

**Durable records:** v2 inherits (does not rewrite) the v1-locked `sst2_per_example.csv` + `sst2_per_example_sha256.txt`; the inherited hash is recorded in the v2 results meta.

If a valid band exists: `τ_lo`, `τ_hi` (with the supporting distributions) are frozen into `PRE_REGISTRATION_SST2_NEGATION_OVP.md` (lock 2) before *its* lock, **and lock 2 must pin the identical standardized estimator** (the cut points are only meaningful for the instantiation that produced them). The inherited per-example materialization is reused by lock 2.

---

## 8. Materialization, lock, execution (ordered steps)

1. **Build-and-smoke** `calibrate_sst2_cutpoints_v2.py` strictly to this pre-reg, smoke on a non-canonical seed (simulated compressed `(B, y)`), confirming the two §3 invariants and that nulls re-center; then the pre-cold-pass **spec↔implementation output-conformance check**.
2. **Cross-pass:** warm review, then **two independent cold passes**, ≥1 cold, fix-author cannot clear.
3. **Lock** (`sst2-ovp-calib-v2-lock`): this pre-reg + `calibrate_sst2_cutpoints_v2.py` + `materialization_manifest_sst2_calib_v2.json` (generator aborts on dataset-hash, model-revision-identity, **and inherited per-example-hash** mismatch), one atomic commit + signed tag.
4. **Run exactly once** (no flags) → read + hash-verify the inherited `(B, y)`; produce `τ_lo`, `τ_hi`, the HDG distributions (AUC + AP), and the §6 result — persisting exactly the §7 set.
5. **Freeze** outputs into lock 2 (or, if MIS-SPECIFIED, publish that finding and stop; the negation study does not proceed).

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run. The outcome is recorded regardless of whether a band emerges.

---

## 9. What this establishes / does not (restated)

- **Does:** fix the SST-2-specific HDG cut points under a standardized-feature logistic (or honestly report MIS-SPECIFIED), sourced independently of the candidate run; and, via the held-fixed seed, establish a controlled contrast isolating the effect of standardization against v1.
- **Does not:** judge negation; validate OVP; move the §6 ladder; generalize beyond this substrate–instrument pairing.

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; the fix-author (including the AI collaborator) cannot be a clearing reader. A warm pass against the pinned pre-commitments precedes the cold passes; it does not substitute for them. The pre-cold-pass build-and-smoke + output-conformance check is a precondition (per `OVP_DESIGN_HISTORY.md`). Recorded in `CROSSPASS_SST2_OVP_CALIB_v2.md`.

---

## 11. Discretionary pins (pinned as written; for explicit pre-lock sign-off)

1. Primary metric AUC; sensitivity panel AP on the **error class** (relabel `1 − y`, score `1 − P(correct)`), computed from the standardized-estimator predictions.
2. Resampling: repeated stratified 50/50 splits — the single scheme; **no bootstrap** (partition-variance estimand).
3. `R_cal = 200`; full 872 examples re-split each replication.
4. Meaningful sweep `σ_m` grid {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}; null forms (`2B−1`, `N(0,1)`); percentile rule (max-of-95ths `τ_lo`, P5-of-weakest-clearing `τ_hi`); margin `δ = 0.01`.
5. **Estimator (the v2 pin): `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, solver='lbfgs'))`, fit on the training partition only (scaler statistics never see the held-out split).** The sole change from v1's unstandardized logistic.
6. **Seed `0x55712` — deliberately identical to v1** for a controlled one-variable contrast (justified in §3; not seed-shopping since v1 already ran to a fixed outcome); numpy `'linear'` percentile interpolation.
7. Substrate inherited from the v1 lock: dataset sha `a0b4a680…2588376d`, model revision `714eb0fa…`, per-example `sst2_per_example.csv` sha `e9e5b12a…b7bec1c7` (verified at run and at lock; abort on mismatch).

*End of draft pre-registration. Awaiting build-and-smoke + warm pass + two cold passes; not locked.*

---

## 12. Relationship to SST2_OVP_CALIB v1 (new lock, not a re-run)

v1 (`sst2-ovp-calib-lock` / `-result`) remains the immutable, cited record of the **unstandardized-estimator** finding (MIS-SPECIFIED via check 1). v2 is a **separate pre-registration and lock** that changes exactly one pin and re-asks the calibration question; it neither edits nor re-executes v1. Both outcomes stand on the record. If v2 yields a band, the negation study (lock 2) inherits v2's cut points **and** v2's standardized estimator; if v2 is also MIS-SPECIFIED, the combined v1+v2 record is the substrate-level finding described in §6.
