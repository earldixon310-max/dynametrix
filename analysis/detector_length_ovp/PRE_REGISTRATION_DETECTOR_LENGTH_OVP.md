# Pre-Registration — DETECTOR_LENGTH_OVP (candidate study; OVP real candidate #2)

**Study type:** OVP **real candidate** study — judges whether the candidate observable **`text_length`** (the input's full token count under the detector's tokenizer) adds Held-out Discriminative Gain (HDG) beyond the baseline (detector confidence) in predicting ChatGPT-detector correctness. It is the **second real candidate** on the ChatGPT-detector substrate, judged against the **same locked calibration band** as DETECTOR_TRUNCATION_OVP.
**Governing spec:** OVP v0.1, locked at signed tag `ovp-v0.1-lock` (tag-only/byte-exact). Conforms to the spec at that tag.
**Admissibility:** OVP_POSCONTROL_v1 PASSED; real candidate verdicts are admissible. Cut points inherited from the separate, locked calibration `DETECTOR_OVP_CALIB` (`detector-ovp-calib-result`), per spec §1 provenance.
**Status:** DRAFT — not locked. (Review-progress in `CROSSPASS_DETECTOR_LENGTH_OVP.md`.)

---

## 0. Architectural framing — what this study tests, and why `text_length`

```
DETECTOR_OVP_CALIB        → froze the ChatGPT-detector HDG band [τ_lo, τ_hi] (USABLE BAND; locked)
DETECTOR_TRUNCATION_OVP   → `truncated` → Inconclusive (real verdict #1)
DETECTOR_LENGTH_OVP       → THIS study: `text_length` → real verdict #2
```

**The scientific question.** Verdict #1 found `truncated` Inconclusive: it has a strong *marginal* association with correctness (truncated-input accuracy 0.848 vs 0.656) but a small *incremental* gain beyond confidence — i.e., **the detector's confidence approximately encodes the reliability information that input-truncation carries.** `text_length` is the **continuous parent of `truncated`** (`truncated = 1[text_length > 512]`), so it directly tests **how far that "confidence-is-a-sufficient-statistic" relationship extends beyond the truncation ceiling**:

- **Validated** (`D > τ_hi`): continuous length carries reliability information beyond what the binary truncation flag captured *and* beyond confidence — confidence is **not** sufficient for length-related uncertainty across the full range.
- **Not-Validated** (`D < τ_lo`): length adds nothing demonstrable — confidence is (under this estimator) approximately a **sufficient statistic for length-class signals**; a methodological result about the detector, not just the feature.
- **Inconclusive** (`τ_lo ≤ D ≤ τ_hi`): length, like truncation, sits in the band — confidence broadly captures length-class uncertainty; reinforces verdict #1's pattern.

Each outcome advances OVP toward the **operational** rung (≥3 real verdicts; this is #2) **and** says something real about the detector.

**Does not:** decide `text_length`'s scientific interest/use; separate redundant-from-additive (v0.2); generalize beyond this substrate/estimator/metric; reach operational on its own.

---

## 1. Objective

Determine whether **`text_length`** (full token count under the detector's pinned tokenizer) carries out-of-sample information about **detector correctness** beyond the detector's own **confidence**, judged against the externally-frozen calibration band.

---

## 2. Substrate and materialization (B, y inherited; text_length materialized fresh; cross-checked)

- **Model/dataset (pinned):** identical to the calibration — `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c61775d5dd0221808a79983ed3b86ffd86` (AI-class index 1, `max_length=512`) over the RAID test subsample sha256 `a29f8f2c…ff615a47`.
- **`B`, `y`, `truncated` — inherited, hash-verified, not re-materialized.** Read the calibration-locked `../detector_truncation_ovp/detector_per_example.csv` and verify its sha256 against the pinned anchor **`24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643`**, aborting on mismatch. Supplies per example `B` = confidence, `y` = correctness, and `truncated`.
- **`text_length` — materialized fresh (tokenizer only, no model inference):** for each example, `text_length = len(tokenizer(text, truncation=False)["input_ids"])` using the **pinned tokenizer at the same revision**, over the hash-verified RAID test set, aligned to the inherited rows by `id`. Tokenization is deterministic; no model weights needed.
- **Materialization cross-check (integrity guard, pinned):** `(text_length > 512).astype(int)` **must equal the inherited `truncated` column elementwise**; any mismatch **aborts** (this validates tokenizer determinism, the 512-window definition, and row alignment simultaneously). Written to `detector_length_per_example.csv` (`id, B, y, truncated, text_length`) with a SHA-256.

---

## 3. Baseline, candidate, and §2 baseline-rule conformance

- **Baseline `B`:** detector **confidence** (max softmax) — a single scalar, the simplest substrate-native predictor of its own correctness.
- **Candidate observable `C`:** **`text_length`** (full token count; continuous, integer-valued).
- **Ancestry Statement (spec §2 criterion 5, on the record):** **`text_length` (the input's full token count under the detector's tokenizer) extends `confidence` (the detector's own max-softmax self-assessment of its correctness): an input-scale property that may modulate the detector's reliability extends the model's internal certainty signal.** The claim under test is that *how long the input is* carries information about when the detector errs that its own confidence does not already encode — the continuous generalization of the truncation question. (Per §2, baseline selection is not valid without this statement; stated here before any candidate-vs-baseline computation.)
- **§2 criteria (all five hold):** (1) **same substrate** — `B` and `text_length` both derive from the same pinned model+data; (2) **strictly simpler** — baseline uses `B` alone (1 feature), candidate adds `text_length` (2 features), so `B` is strictly simpler, and `B` is no more complex than the candidate; (3) **pre-registered** — committed at lock, no post-lock substitution; (4) **no post-hoc** — never chosen/tuned/swapped after results; (5) **Ancestry Statement** — above. Conforms.

---

## 4. HDG instantiation (pinned; inherited from the calibration)

- **Measure (spec §1):** `D` = HDG = `AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`, out-of-sample, AUC higher-is-better.
- **Estimator (identical to the calibration / truncation study):** `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True))`, **fit on the training partition only** (scaler from train rows, applied to held-out; no leakage). `text_length` is z-scored by the same scaler (its integer scale is handled by standardization). Mandatory identical reuse — the cut points are valid only for this instantiation.
- **Split protocol:** repeated **stratified 50/50 train/test splits** on `y`, **R = 200**, baseline and candidate **paired** (same train/test rows per replication). **Master seed `0x73C0DE`** — fresh, distinct from the calibration (`0xD37EC7`), truncation (`0x77C0DE`), and all prior. `SeedSequence(master).spawn(R)`, one child per replication.
- **The scalar `D` (pinned, identical form to verdict #1):** `D = median(HDG_AUC[1..200])` — ordinary median (numpy `'linear'`/type-7) over **all 200** replications, **no trimming/winsorizing/sub-selection**; the verdict reads this single `D`. (Mean, P5, P95, per-region fractions reported as non-gating support.)
- **Sensitivity panel (non-gating):** error-class **AP** (relabel `1−y`, score `1−P(correct)`), median over the splits.

---

## 5. Inherited cut points (frozen; verbatim from the calibration result)

Quoted verbatim from `../detector_truncation_ovp/detector_calibration_results.json` (locked `detector-ovp-calib-result`):

- **`τ_lo = 0.02458901317356486`**
- **`τ_hi = 0.06829080323934116`**

**Provenance (spec §1):** external — the separate, pre-lock, independently-locked calibration under seed `0xD37EC7`, never sourced from this candidate's run. **Runtime guard (pinned):** the locked `judge_length.py` asserts its hardcoded `TAU_LO`/`TAU_HI` are byte-identical to the calibration result at every run start (`verify_cut_points`), aborting on drift, complementing the lock-time manifest check.

---

## 6. Verdict rule (spec §6; pinned)

Read from the scalar `D` against the inherited band:

- **Validated** — `D > τ_hi` (`> 0.06829080323934116`).
- **Not-Validated** — `D < τ_lo` (`< 0.02458901317356486`): mechanism-agnostic in v0.1.
- **Inconclusive** — `τ_lo ≤ D ≤ τ_hi`: closed ambiguity band; abstention, recorded with parity.

All three pre-committed and published identically; the verdict type is not predicted here. Guards: inherited per-example-hash (§2), the materialization cross-check (§2), estimator-identity (§4), runtime cut-point assert (§5). Any guard failure invalidates the run (amended under a new tag), never silently proceeds.

---

## 7. Outputs (persistence contract)

To `detector_length_results.json`, the single run writes (and nothing beyond): the scalar **`D` (median HDG)** + **verdict**; echoed `τ_lo`/`τ_hi` + `band_relation`; the **full per-replication HDG arrays** (AUC and error-class AP, R=200) under `hdg_distribution`; non-gating support (HDG mean/P5/P95; fractions above-`τ_hi`/below-`τ_lo`/in-band; AP median); `n_examples`, `n_errors`, plus `text_length` summary (`min`/`median`/`max`, `truncated_prevalence`); and full meta (candidate/baseline labels, canonical+used seed, canonical+used R, model id+revision, dataset sha, inherited per-example sha, materialized length-file sha, estimator descriptor, cut-point provenance tag, UTC). Becomes the second OVP ledger row (spec §5).

---

## 8. Build-and-smoke, cross-pass, lock, execution (ordered)

1. **Build-and-smoke** `judge_length.py` strictly to this pre-reg. **No-peeking: running `judge_length.py` (any flags) always computes `text_length`'s real HDG and is NOT the smoke;** the smoke is a **separate synthetic harness** loading only `B`, `y` (never `text_length`) that confirms a known-null → Not-Validated and a known-meaningful → Validated, and that the inherited-hash / materialization-cross-check / cut-point guards fire. Then the output-conformance check.
2. **Cross-pass:** warm review, then **two independent cold passes** (≥1 cold, fix-author cannot clear).
3. **Lock** (`detector-length-ovp-lock`): this pre-reg + `judge_length.py` + `materialization_manifest_detector_length.json` (aborts on inherited per-example-hash, dataset-hash, model-revision-identity, or cut-point-identity mismatch), one atomic commit + signed tag.
4. **Run exactly once** (no flags) → materialize `text_length` + cross-check vs `truncated`; compute `{D_r}`, `D = median`, the verdict; persist §7.
5. **Write the result** (`RESULT_DETECTOR_LENGTH_OVP.md`), route its cold cross-pass (citation gate), record the second ledger row. Published regardless of outcome.

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run.

---

## 9. What this establishes / does not

- **Does:** issue OVP's second real candidate verdict — whether `text_length` adds HDG beyond confidence under the pinned standardized linear estimator, against externally-frozen cut points; record it with parity; test the extent of the confidence-sufficiency relationship surfaced by verdict #1.
- **Does not:** judge scientific interest/use; separate redundant-vs-additive (v0.2); generalize beyond this substrate/estimator/metric; reach operational alone (this is #2 of ≥3).

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; fix-author cannot clear. A warm pass precedes the cold passes; build-and-smoke + output-conformance check is a precondition. Both pass verdicts carried into the ledger row (spec §5/§7).

---

## 11. Discretionary pins (for explicit pre-lock sign-off)

1. Candidate `C = text_length` (full untruncated token count under the pinned tokenizer); baseline `B = confidence`.
2. `D = median(HDG_AUC[1..200])` — ordinary median, all 200, no trimming (mean/percentiles/fractions non-gating support).
3. Estimator: `Pipeline(StandardScaler(train-fit), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, lbfgs))` — identical to the calibration; paired splits.
4. Cut points inherited verbatim `τ_lo = 0.02458901317356486`, `τ_hi = 0.06829080323934116` (provenance `detector-ovp-calib-result`); asserted at runtime and lock.
5. Seed `0x73C0DE` (fresh); R = 200; numpy `'linear'` percentiles for support.
6. Substrate: `B,y,truncated` inherited from `detector_per_example.csv` sha `24dac078…01afc643`; `text_length` materialized fresh via the pinned tokenizer over dataset `a29f8f2c…`, with the `1[text_length>512]==truncated` cross-check (abort on mismatch).
7. Error-class AP as the non-gating sensitivity panel.

*End of draft pre-registration. Awaiting build-and-smoke + warm pass + two cold passes; not locked.*

---

## 12. Relationship to verdict #1 and the ledger

Inherits the calibration's cut points, estimator, and `(B, y)` from the locked detector arc without re-litigating them; materializes only the new candidate `text_length`, cross-checked against the inherited `truncated`. Its verdict is OVP's second ledger row, recorded with parity whichever way it lands, and — read against verdict #1 — characterizes how far the detector's confidence-as-sufficient-statistic property extends from the truncation ceiling across the full length range.
