# Pre-Registration — DETECTOR_DIRECTION_OVP (candidate study; OVP real candidate #3)

**Study type:** OVP **real candidate** study — judges whether the candidate observable **`predicted_prob_ai`** (the detector's raw *directional* probability) adds Held-out Discriminative Gain (HDG) beyond the baseline **`confidence`** (the *folded* magnitude) in predicting ChatGPT-detector correctness. Third real candidate on the ChatGPT-detector substrate, judged against the same locked calibration band. **This verdict, whatever its outcome, is the third real ledger entry — reaching the §6 operational rung** (≥3 real verdicts of any outcome).
**Governing spec:** OVP v0.1 @ `ovp-v0.1-lock` (tag-only/byte-exact). Conforms to the spec at that tag.
**Admissibility:** OVP_POSCONTROL_v1 PASSED; real candidate verdicts admissible. Cut points inherited from the separate, locked calibration `DETECTOR_OVP_CALIB` (`detector-ovp-calib-result`), per spec §1 provenance.
**Status:** DRAFT — not locked. (Review-progress in `CROSSPASS_DETECTOR_DIRECTION_OVP.md`.)

---

## 0. Architectural framing — the question, and why it differs from #1/#2

```
DETECTOR_OVP_CALIB        → froze the ChatGPT-detector HDG band [τ_lo, τ_hi] (USABLE BAND; locked)
DETECTOR_TRUNCATION_OVP   → `truncated`    → Inconclusive   (real verdict #1; citable)
DETECTOR_LENGTH_OVP       → `text_length`  → Not-Validated  (real verdict #2; citable)
DETECTOR_DIRECTION_OVP    → THIS study: `predicted_prob_ai` → real verdict #3 → OPERATIONAL rung
```

**The question.** Verdicts #1 and #2 were both *input-structure* features (truncation, length) and both came back non-positive: the detector's confidence absorbs input-shape signal. This candidate asks a different question about the model's **own output**: does the **direction** of the probability (leaning toward Human vs toward ChatGPT) carry correctness information that the *folded* confidence (`B = max(p, 1−p)`) discards? Equivalently: **is the detector's reliability class-asymmetric** — is it more trustworthy when it leans one way than the other? If the model is equally accurate on AI-leaning and Human-leaning predictions, direction is uninformative; if asymmetric, direction predicts correctness.

**Does:** issue OVP's third real verdict (reaching operational); characterize class-asymmetric reliability of the detector under the pinned linear estimator. **Does not:** decide scientific interest/use; separate redundant-vs-noise on a Not-Validated (v0.2); generalize beyond this substrate/estimator/metric.

---

## 1. Objective

Determine whether the **raw directional probability `predicted_prob_ai`** carries out-of-sample information about **detector correctness** beyond the **folded confidence** `B`, judged against the externally-frozen calibration band.

---

## 2. Substrate and materialization (everything inherited; no new materialization)

- **Model/dataset (pinned):** identical to the calibration — `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c61775d5dd0221808a79983ed3b86ffd86` over the RAID test subsample sha256 `a29f8f2c…ff615a47`.
- **All quantities inherited, hash-verified, NOT re-materialized.** Read the calibration-locked `../detector_truncation_ovp/detector_per_example.csv` and verify its sha256 against the pinned anchor **`24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643`**, aborting on mismatch. It already contains, per example: `B = B_confidence` (folded confidence = `max(p, 1−p)`), `y = y_correct`, the candidate **`predicted_prob_ai` = `p`** (raw directional probability), and `pred` (the predicted class, used only for non-gating per-class diagnostics). **No tokenizer, no model inference, no new materialization** — this is the simplest candidate study in the arc; `(B, y, p)` are byte-identical to the calibration substrate.

---

## 3. Baseline, candidate, and §2 baseline-rule conformance

- **Baseline `B`:** detector **confidence** = `max(p, 1−p)` — the *folded* (sign-discarding) magnitude.
- **Candidate observable `C`:** **`predicted_prob_ai` = `p`** — the raw, *directional* probability.
- **Ancestry Statement (spec §2 criterion 5, on the record):** **`predicted_prob_ai` (the detector's raw *directional* probability that the input is AI) extends `confidence` (the *folded* magnitude `max(p, 1−p)`): the raw probability adds back the *direction* the fold discards.** The baseline is a deterministic lossy folding of the candidate (`B = max(C, 1−C)`), so the candidate strictly contains it. **Why this is the right candidate (not the predicted-class bit):** under the pinned *linear* estimator, `[B, p]` and `[B, pred]` are **not** equivalent. `[B, p]`'s linear predictor `w_B·B + w_p·p` resolves to slope `(w_B+w_p)·B` for `pred=1` and `(w_B−w_p)·B + w_p` for `pred=0` — a **class-specific slope** plus intercept; whereas `[B, pred] = w_B·B + w_pred·pred` forces an identical slope on both classes and shifts only the intercept. So `[B, p]` and `[B, pred]` are **non-nested** under the linear estimator: `[B, p]` captures a **class-specific slope** (with a coupled intercept), while `[B, pred]` captures a **pure parallel intercept shift** that `[B, p]` *cannot* represent (that would require the `p` coefficient to vanish, deleting the term). **Neither strictly dominates the other.** Raw `p` is chosen because it tests the **slope-asymmetry axis** — generally the more sensitive and interpretable form of class-asymmetric reliability — and because it is the model's actual directional output. It is **not** strictly more powerful than `pred`: a *pure-intercept* asymmetry (equal slopes, shifted intercept) would be detected by `[B, pred]` but **missed** by `[B, p]`. (The required §2 Ancestry relation — `B = max(p, 1−p)` is a deterministic lossy fold of `p` — holds regardless and is what makes `p` an admissible candidate.)
- **§2 criteria (all five hold):** (1) **same substrate** — `B` and `p` both the same model output; (2) **strictly simpler** — baseline `[B]` (1 feature) vs candidate `[B, p]` (2 features), and `B = max(p,1−p)` is a lossy coarsening of `p`, so `B` is strictly simpler and no more complex than the candidate; (3) **pre-registered**; (4) **no post-hoc**; (5) **Ancestry Statement** — above. Conforms. *(Note: `B` and `p` relate in a V-shape — `B=p` for `p≥0.5`, `B=1−p` for `p<0.5` — so `[B, p]` is full-rank; no collinearity degeneracy.)*

---

## 4. HDG instantiation (pinned; inherited from the calibration)

- **Measure (spec §1):** `D` = HDG = `AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`, out-of-sample, AUC higher-is-better.
- **Estimator (identical to the calibration / #1 / #2):** `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True))`, **fit on the training partition only** (no leakage). `p` is z-scored by the same scaler. Mandatory identical reuse — the cut points are valid only for this instantiation. *(Under this linear estimator, the augmented model captures class-specific slope+intercept asymmetry; see §3.)*
- **Split protocol:** repeated **stratified 50/50 train/test splits** on `y`, **R = 200**, baseline and candidate **paired** (same train/test rows per replication). **Master seed `0xDEC0DE`** — fresh, distinct from the calibration (`0xD37EC7`), #1 (`0x77C0DE`), #2 (`0x73C0DE`), and all prior. `SeedSequence(master).spawn(R)`, one child per replication.
- **The scalar `D` (pinned, identical form to #1/#2):** `D = median(HDG_AUC[1..200])` — ordinary median (numpy `'linear'`/type-7) over **all 200**, **no trimming/winsorizing/sub-selection**; the verdict reads this single `D`. (Mean/P5/P95/per-region fractions reported as non-gating support.)
- **Sensitivity panel (non-gating):** error-class **AP** (relabel `1−y`, score `1−P(correct)`), median over the splits.

---

## 5. Inherited cut points (frozen; verbatim from the calibration result)

Quoted verbatim from `../detector_truncation_ovp/detector_calibration_results.json` (locked `detector-ovp-calib-result`):

- **`τ_lo = 0.02458901317356486`**
- **`τ_hi = 0.06829080323934116`**

**Provenance (spec §1):** external — the separate, pre-lock, independently-locked calibration under seed `0xD37EC7`, never sourced from this candidate's run. **Runtime guard (pinned):** the locked `judge_direction.py` asserts its hardcoded `TAU_LO`/`TAU_HI` are byte-identical to the calibration result at every run start (`verify_cut_points`), aborting on drift; complemented by the lock-time manifest check.

---

## 6. Verdict rule (spec §6; pinned)

Read from the scalar `D` against the inherited band:

- **Validated** — `D > τ_hi` (`> 0.06829080323934116`): direction adds out-of-sample structure beyond folded confidence (class-asymmetric reliability).
- **Not-Validated** — `D < τ_lo` (`< 0.02458901317356486`): mechanism-agnostic in v0.1.
- **Inconclusive** — `τ_lo ≤ D ≤ τ_hi`: closed ambiguity band; abstention, recorded with parity.

All three pre-committed and published identically; the verdict type is not predicted here. Guards: inherited per-example-hash (§2), estimator-identity (§4), runtime cut-point assert (§5). Any guard failure invalidates the run (amended under a new tag), never silently proceeds.

---

## 7. Outputs (persistence contract)

To `detector_direction_results.json`, the single run writes (and nothing beyond): the scalar **`D`** + **verdict**; echoed `τ_lo`/`τ_hi` + `band_relation`; the **full per-replication HDG arrays** (AUC and error-class AP, R=200) under `hdg_distribution`; non-gating support (HDG mean/P5/P95; fractions above-`τ_hi`/below-`τ_lo`/in-band; AP median); `n_examples`, `n_errors`; **non-gating per-predicted-class diagnostics** (`accuracy | pred=1`, `accuracy | pred=0`, and their counts — computed once in the locked run, to support the §9 slope-vs-intercept interpretation if Validated); and full meta (candidate/baseline labels, canonical+used seed, canonical+used R, model id+revision, dataset sha, inherited per-example sha, estimator descriptor, cut-point provenance tag, UTC). Becomes the **third** OVP ledger row (spec §5).

---

## 8. Build-and-smoke, cross-pass, lock, execution (ordered)

1. **Build-and-smoke** `judge_direction.py` strictly to this pre-reg. **No-peeking — heightened for this candidate:** the directional marginal (accuracy-by-predicted-class) is close enough to the HDG that it is **not computed pre-lock**; running `judge_direction.py` (any flags) always computes `p`'s real HDG and is NOT the smoke; the smoke is a **separate synthetic harness** loading only `B`, `y` (never `p`/`pred`) that confirms a known-null → Not-Validated and a known-meaningful → Validated, and that the inherited-hash / cut-point guards fire. Then the output-conformance check.
2. **Cross-pass:** warm review, then **two independent cold passes** (≥1 cold, fix-author cannot clear).
3. **Lock** (`detector-direction-ovp-lock`): this pre-reg + `judge_direction.py` + `materialization_manifest_detector_direction.json` (aborts on inherited per-example-hash, dataset-hash, model-revision-identity, or cut-point-identity mismatch), one atomic commit + signed tag.
4. **Run exactly once** (no flags) → read+verify inherited `(B, y, p, pred)`; compute `{D_r}`, `D = median`, the verdict, the per-class diagnostics; persist §7.
5. **Write the result** (`RESULT_DETECTOR_DIRECTION_OVP.md`), route its cold cross-pass (citation gate), record the third ledger row → **operational rung reached.**

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run.

---

## 9. What this establishes / does not

- **Does:** issue OVP's third real verdict — whether directional `predicted_prob_ai` adds HDG beyond folded confidence under the pinned linear estimator — **reaching the operational rung**; characterize class-asymmetric reliability.
- **Interpretation hooks (non-gating):** if **Validated**, the gain came from the **slope-asymmetry axis** `[B, p]` spans; the per-class diagnostics (acc|pred=1 vs acc|pred=0) separately report the *intercept-level* asymmetry (different base accuracy by predicted class) — together they characterize the asymmetry, reported in the result doc post-hoc, clearly labeled non-gating. If **Not-Validated/Inconclusive**, the supported null is scoped to what `[B, p]` can detect: **no slope-type class-asymmetry on the coupled axis `[B, p]` spans.** It does **not** rule out a *pure-intercept* asymmetry (equal slopes, shifted intercept), which `[B, p]` cannot represent — establishing that would be a separate `[B, pred]`-shaped study. (Corrected from an earlier draft that overstated this as a symmetric null in *both* slope and intercept.)
- **Does not:** decide scientific interest/use; separate redundant-vs-noise (v0.2); generalize beyond this substrate/estimator/metric — in particular says nothing about a nonlinear estimator.

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; fix-author cannot clear. A warm pass precedes the cold passes; build-and-smoke + output-conformance check is a precondition. Both pass verdicts carried into the ledger row (spec §5/§7).

---

## 11. Discretionary pins (for explicit pre-lock sign-off)

1. Candidate `C = predicted_prob_ai` (raw directional probability); baseline `B = confidence` (folded `max(p,1−p)`).
2. `D = median(HDG_AUC[1..200])` — ordinary median, all 200, no trimming (mean/percentiles/fractions + per-class accuracy non-gating support).
3. Estimator: `Pipeline(StandardScaler(train-fit), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, lbfgs))` — identical to the calibration; paired splits.
4. Cut points inherited verbatim `τ_lo = 0.02458901317356486`, `τ_hi = 0.06829080323934116` (provenance `detector-ovp-calib-result`); asserted at runtime + lock.
5. Seed `0xDEC0DE` (fresh); R = 200; numpy `'linear'` percentiles for support.
6. Substrate: all of `B,y,predicted_prob_ai,pred` inherited from `detector_per_example.csv` sha `24dac078…01afc643` (hash-verified); no new materialization.
7. Error-class AP as the non-gating sensitivity panel; per-predicted-class accuracy as a non-gating interpretation diagnostic.

*End of draft pre-registration. Awaiting build-and-smoke + warm pass + two cold passes; not locked.*

---

## 12. Relationship to verdicts #1/#2 and the operational rung

Inherits the calibration's cut points, estimator, and `(B, y)` from the locked detector arc; the candidate `predicted_prob_ai` is already in the inherited per-example (no new materialization). This is the third real candidate; its verdict — Validated, Not-Validated, or Inconclusive — is OVP's third ledger row and **reaches the operational rung (§6.2: ≥3 real verdicts of any outcome)**, transitioning OVP from *self-validated* to *operational*. Read against #1/#2 (both input-structure non-positives), it adds the model-output / class-asymmetry axis to the ledger's characterization of the detector.
