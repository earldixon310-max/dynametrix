# Pre-Registration — DETECTOR_TRUNCATION_OVP (candidate study; lock 2)

**Study type:** OVP **real candidate** study — judges whether the candidate observable **`truncated`** adds Held-out Discriminative Gain (HDG) beyond the baseline (detector confidence) in predicting ChatGPT-detector correctness. **Lock 2 of the two-lock arc**; it produces **OVP's first real candidate-observable verdict** for the ledger.
**Governing spec:** OVP v0.1, locked at signed tag `ovp-v0.1-lock` (tag-only/byte-exact; verify `git tag -v ovp-v0.1-lock`). Conforms to the spec at that tag.
**Admissibility:** OVP_POSCONTROL_v1 **PASSED** (the protocol's positive control), so real candidate verdicts are admissible to the ledger (spec §4/§9). The cut points are inherited from a **separate, locked, externally-provenanced calibration** (DETECTOR_OVP_CALIB), per spec §1 provenance rule.
**Status:** DRAFT — not locked. (Review-progress tracked in `CROSSPASS_DETECTOR_TRUNCATION_OVP.md`, not narrated here.)

---

## 0. Architectural framing and what this study does / does not establish

```
OVP_POSCONTROL_v1        → instrument validated on synthetic ground truth (PASS)
DETECTOR_OVP_CALIB       → froze the ChatGPT-detector HDG band [τ_lo, τ_hi] (USABLE BAND; locked)
DETECTOR_TRUNCATION_OVP  → THIS study: judges `truncated` against that band → first real ledger verdict
```

**Does:** render exactly one v0.1 verdict — **Validated / Not-Validated / Inconclusive** — on whether `truncated` adds out-of-sample discriminative structure beyond detector confidence, under the pinned standardized estimator, judged against externally-sourced cut points. The verdict (whatever it is) is recorded with positive-result parity as the **first real row** in the OVP ledger, advancing OVP toward the **operational** rung (≥3 real verdicts).

**Does not:** decide whether `truncated` is *scientifically interesting or useful* (spec §0); separate *redundant-from-baseline* vs *noise-like* if Not-Validated (that is v0.2's four-verdict job); validate OVP generally; generalize beyond this substrate–instrument pairing. A Not-Validated here is **mechanism-agnostic** by design.

---

## 1. Objective

Determine whether the candidate observable **`truncated`** (whether the input text exceeded the detector's 512-token window) carries out-of-sample information about **detector correctness** beyond what the detector's own **confidence** already provides — i.e., whether adding `truncated` to a confidence-only discriminator raises held-out AUC by more than the pre-registered band allows for noise.

---

## 2. Substrate and materialization (inherited from the calibration lock; not re-run)

- **Model/dataset (pinned):** identical to DETECTOR_OVP_CALIB — `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c61775d5dd0221808a79983ed3b86ffd86` (AI-class index 1, `max_length=512`) over the RAID test subsample sha256 `a29f8f2c…ff615a47`.
- **Per-example data — inherited, hash-verified, not re-materialized.** This study **reads the calibration-locked `detector_per_example.csv`** (tag `detector-ovp-calib-result`) and verifies its sha256 against the pinned anchor **`24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643`** (and `detector_per_example_sha256.txt`), aborting on mismatch. It supplies, per example: **`B` = confidence** (max softmax), **`y` = correctness** (`pred == is_ai_generated`), and **`truncated`** ∈ {0,1} (full-token-len > 512). No model re-run; `(B, y, truncated)` are byte-identical to the calibration substrate.
- **Substrate profile (context):** n = 2000, accuracy 0.678, errors 644; `truncated` prevalence ≈ 0.116 (≈231 of 2000).

---

## 3. Baseline, candidate, and §2 baseline-rule conformance

- **Baseline `B`:** the detector's **confidence** (max softmax probability) — a single scalar, the simplest substrate-native predictor of its own correctness.
- **Candidate observable `C`:** **`truncated`** ∈ {0,1}.
- **Ancestry Statement (spec §2 criterion 5, on the record):** **`truncated` (whether the input text exceeded the detector's 512-token context window) extends `confidence` (the detector's own max-softmax self-assessment of its correctness): an input-structural property the model may systematically mishandle extends the model's internal certainty signal.** The claim under test is that *whether the detector even saw the whole input* carries information about when it errs that its own confidence does not already encode. (Per §2, baseline selection is not valid without this statement; it is stated here before any candidate-vs-baseline computation.)
- **§2 baseline-selection criteria (all five hold):** (1) **same substrate** — both `B` and `truncated` derive from the same pinned model+data; (2) **strictly simpler** — the baseline discriminator uses `B` alone (1 feature), the candidate model adds `truncated` (2 features), so `B` is strictly simpler than baseline+candidate, and `B` (confidence) is itself no more complex than the candidate; (3) **pre-registered** — `B` is committed at the lock commit, no post-lock substitution; (4) **no post-hoc clause** — `B` is never chosen, tuned, or swapped after results; (5) **Ancestry Statement** — provided above. Conforms.

---

## 4. HDG instantiation (pinned; inherited from the calibration)

- **Measure (spec §1, fixed by the version):** `D` = HDG = `AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`, out-of-sample, AUC higher-is-better.
- **Estimator / function class (pinned — identical to DETECTOR_OVP_CALIB):** `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True))`, **fit on the training partition only** (scaler statistics from train rows, applied to held-out rows; no test leakage). The cut points are valid only for this instantiation; reusing it exactly is mandatory.
- **Split protocol (pinned):** repeated **stratified 50/50 train/test splits** stratified on `y`, **R = 200** replications (matching the calibration's estimation variance). **Master seed `0x77C0DE`** — fresh, distinct from the calibration (`0xD37EC7`) and all prior studies. Seed derivation: `SeedSequence(master).spawn(R)`, one child per replication; within a replication the baseline and candidate models share the *same* split (the HDG is a paired baseline-vs-candidate contrast on identical train/test rows — this is the one place pairing matters, and unlike the calibration's marginal-only use, it is pinned here).
- **The scalar `D` (the one design decision; spec leaves the per-study summary open):** `D` = the **median** of the per-replication HDG `{D_r}` over the R = 200 splits. **Unambiguous mechanical form (pinned):** `D = median(HDG_AUC[1..200])` — the ordinary median (numpy `'linear'` / type-7) over **all 200** replications, **no trimming, no truncation, no winsorizing, no sub-selection**; the verdict (§6) reads this single `D` against the inherited `τ_lo` and `τ_hi` as a deterministic function. Median (robust central value) is the pinned scalar. Rationale: τ_lo/τ_hi are conservative distribution *tails* (P95 of noise, P5 of the weakest meaningful), so the symmetric candidate-side quantity is the central value of `truncated`'s HDG distribution; and the median resists the heavy-tailed per-split AUC-difference noise that a small (~1000-example) test fold produces, so one anomalous split cannot flip a near-boundary verdict. (Mean, P5, P95, and per-region fractions are **reported as non-gating support** so a reader can audit whether the central-statistic choice is decision-relevant — the locked run commits to median as the gating scalar but does not foreclose that audit.)
- **Sensitivity panel (reported, not gating):** error-class **AP** (relabel `1−y`, score `1−P(correct)`), median over the same splits — reported alongside `D`; never enters the verdict.

---

## 5. Inherited cut points (frozen; verbatim from the calibration result)

From `DETECTOR_OVP_CALIB` (locked `detector-ovp-calib-lock`, executed `detector-ovp-calib-result`), quoted verbatim from `detector_calibration_results.json`:

- **`τ_lo = 0.02458901317356486`**
- **`τ_hi = 0.06829080323934116`**
- (context, non-operative: `σ_m_at_τ_hi = 1.5`; `0 < τ_lo < τ_hi`, gap 0.043702 ≥ δ.)

**Provenance (spec §1):** external to this study — a separate, pre-lock, independently-locked calibration study under its own seed (`0xD37EC7`), never sourced from this candidate's run. Frozen before this study runs; not tunable.

**Runtime inheritance guard (pinned):** the locked `judge_truncation.py` asserts its hardcoded `TAU_LO`/`TAU_HI` are byte-identical to the calibration result `detector_calibration_results.json` (`detector-ovp-calib-result`) at the start of every run (`verify_cut_points`), aborting on any drift. This makes the inheritance runtime-enforced — a later stale copy-paste or accidental edit aborts rather than silently judging on wrong cut points — complementing the lock-time manifest cut-point check.

---

## 6. Verdict rule (spec §6 three-verdict structure; pinned)

The verdict is read from the scalar `D` (§4) against the inherited band:

- **Validated** — `D > τ_hi` (`D > 0.06829080323934116`): `truncated` adds out-of-sample structure beyond confidence.
- **Not-Validated** — `D < τ_lo` (`D < 0.02458901317356486`): no demonstrated out-of-sample structure beyond confidence (mechanism-agnostic: redundant-with-confidence *or* noise-like — v0.1 cannot distinguish; that is v0.2's job).
- **Inconclusive** — `τ_lo ≤ D ≤ τ_hi`: `D` falls in the pre-registered closed ambiguity band; an abstention, recorded with full parity.

All three outcomes are pre-committed and published identically. The verdict type is **not** predicted here (the protocol determines it). **No setup-control failure conditions** apply beyond the guards — the inherited per-example-hash guard (§2), the estimator-identity (§4), and the runtime cut-point-inheritance assert (§5); any guard failure invalidates the run (documented, amended under a new tag), it does not silently proceed.

---

## 7. Outputs (persistence contract)

Single-execution: the one locked run writes everything needed to audit the verdict without a re-run, and nothing beyond this pinned set, to `detector_truncation_results.json`:

- the scalar **`D` (median HDG)** and the **verdict** string;
- the inherited **`τ_lo`, `τ_hi`** (echoed) and the band-relation (`D` vs each);
- the **full per-replication HDG array** `{D_r}` (R = 200, AUC) under `hdg_distribution`, plus the per-replication error-class AP array;
- support summaries (non-gating): HDG mean, P5, P95; fractions of replications with `D_r > τ_hi`, `D_r < τ_lo`, and in `[τ_lo, τ_hi]`; the error-class AP median;
- `n_examples`, `n_errors`, `truncated_prevalence`;
- meta: **candidate and baseline labels**, canonical+used seed, canonical+used R, model id+revision, dataset sha, inherited per-example sha, estimator descriptor, the calibration result tag the cut points came from, UTC timestamp.

The verdict becomes the first OVP ledger row (spec §5): candidate `truncated`, baseline confidence, substrate ChatGPT-detector-RoBERTa, measure `D` (median HDG via AUC, standardized logistic, stratified 50/50 × 200), cut points + provenance, verdict, and the cross-pass record.

---

## 8. Build-and-smoke, cross-pass, lock, execution (ordered)

1. **Build-and-smoke** `judge_truncation.py` strictly to this pre-reg. **Discipline constraint: the smoke must NOT compute `truncated`'s HDG** — the real verdict is the locked single-execution output and must not be seen pre-lock. **Running `judge_truncation.py` itself (with any flags) always computes `truncated`'s real HDG and is therefore NOT the smoke;** the smoke is a **separate synthetic harness** that loads only `B` and `y` (never the `truncated` column) and exercises the verdict machinery on **synthetic candidates**: a pure-noise binary feature (expected `D` below `τ_lo` → Not-Validated) and a `y`-correlated feature (expected `D` above `τ_hi` → Validated), confirming the rule classifies known cases correctly and the inherited-hash/cut-point guards fire. Then the pre-cold-pass output-conformance check.
2. **Cross-pass:** warm review, then **two independent cold passes** (≥1 cold, fix-author cannot clear).
3. **Lock** (`detector-truncation-ovp-lock`): this pre-reg + `judge_truncation.py` + `materialization_manifest_detector_truncation.json` (aborts on inherited per-example-hash, dataset-hash, model-revision-identity, **or cut-point-identity** mismatch), one atomic commit + signed tag.
4. **Run exactly once** (no flags) → read+verify inherited `(B, y, truncated)`; compute `{D_r}`, `D = median`, the verdict; persist the §7 set.
5. **Write the result** (`RESULT_DETECTOR_TRUNCATION_OVP.md`), route its cold cross-pass (citation gate), and record the ledger row. The verdict is published regardless of outcome.

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run.

---

## 9. What this establishes / does not (restated)

- **Does:** issue OVP's first real candidate verdict — whether `truncated` adds HDG beyond detector confidence, under the pinned standardized linear estimator, against externally-frozen cut points; record it in the ledger with parity.
- **Does not:** judge `truncated`'s scientific interest/use; separate redundant-vs-noise on a Not-Validated; generalize beyond this substrate, estimator, or metric instantiation; move past the **operational** rung on its own (one verdict; the rung needs ≥3).

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; the fix-author (incl. the AI collaborator) cannot be a clearing reader. A warm pass precedes the cold passes; the build-and-smoke + output-conformance check is a precondition. Both pass verdicts are recorded in `CROSSPASS_DETECTOR_TRUNCATION_OVP.md` and carried into the ledger row (spec §5/§7), divergence included.

---

## 11. Discretionary pins (for explicit pre-lock sign-off)

1. Candidate `C = truncated` (binary, full-token-len > 512); baseline `B = confidence` (max softmax).
2. Measure `D` = HDG via AUC; **scalar `D = median(HDG_AUC[1..200])`** — ordinary median over all 200 stratified 50/50 splits, no trimming/truncation/winsorizing (the one open design choice; mean/percentiles/fractions reported as non-gating support).
3. Estimator: `Pipeline(StandardScaler(train-fit), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, lbfgs))` — identical to the calibration; baseline & candidate share the split within each replication (paired).
4. Cut points inherited verbatim: `τ_lo = 0.02458901317356486`, `τ_hi = 0.06829080323934116` (provenance `detector-ovp-calib-result`); asserted byte-identical against `detector_calibration_results.json` at runtime (`verify_cut_points`) and at lock (manifest).
5. Seed `0x77C0DE` (fresh); R = 200; numpy `'linear'` percentiles for support stats.
6. Substrate inherited: `detector_per_example.csv` sha `24dac078…01afc643` (verified at run and lock); model `d2b342c6…`; dataset `a29f8f2c…`.
7. Error-class AP as the non-gating sensitivity panel.

*End of draft pre-registration. Awaiting build-and-smoke + warm pass + two cold passes; not locked.*

---

## 12. Relationship to the calibration and the ledger

This study is the calibration's downstream lock 2; it inherits the calibration's cut points, estimator, and materialization without re-litigating them. Its verdict — Validated, Not-Validated, or Inconclusive — is OVP's first real ledger entry and is recorded with the same standing whichever way it lands. The substrate was chosen because it can support a verdict (the empirical eligibility screen + the locked USABLE BAND); whether `truncated` *earns* one is exactly what the single locked run decides.
