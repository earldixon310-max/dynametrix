# DistilBERT SST-2 Calibration Verification v1 — Outcome

**Test identifier:** `distilbert-sst2-calibration-v1`
**Pre-registration:** `case_studies/distilbert_sst2/PRE_REGISTRATION_DISTILBERT_SST2_v1.md` (locked under git commit `e6f6013` on 2026-05-04)
**Run date:** 2026-05-06 (lock-to-run gap of 2 days while resolving Windows torch DLL configuration; documented in Implementation Observations below)
**Customer:** Earl Dixon (self-audit, public demonstration)
**Auditor:** Earl Dixon
**Status:** Locked outcome. Per pre-registration Section 11, this result document is bound and not subject to revision.

---

## Summary

The DistilBERT model `distilbert-base-uncased-finetuned-sst-2-english` (HuggingFace revision `714eb0fa…`) was evaluated for calibration on the SST-2 validation split (872 examples) under the pre-registered methodology.

**Outcome: Not calibrated.** Of the 2 reliability bins meeting the n ≥ 30 sample-size requirement, **neither passes the Wilson criterion**. The pre-registered decision criteria (Section 6.1) classify this as the strongest falsifying outcome.

The result is striking because it surfaces a contradiction that a pure accuracy test would miss. The model achieves **91.1% accuracy** on the validation set (consistent with the model card's claim) and a **+0.667 Brier skill score** against the base-rate climatology. By any single-number summary of model quality, the model looks excellent. But its probabilities lie about their own reliability: when the model says "99.6% confident positive," the actual frequency of positive examples in that bin is 90.9% — an 8.7-percentage-point overconfidence. When the model says "0.65% chance positive," the actual rate is 6.1% — about 9× higher than the predicted probability suggests.

The model is bimodal and systematically overconfident at both extremes. This is the calibration audit catching what accuracy testing cannot.

---

## Outcome per Pre-Registered Decision Criteria

The following decision rules were locked in advance (pre-registration Section 6.1):

| Outcome | Criterion | Met? |
|---|---|---|
| Calibrated (strong) | ≥ ceil(0.9 × included_bins) bins pass + BSS > 0 | No |
| Calibrated (acceptable) | ≥ ceil(0.8 × included_bins) bins pass + BSS > 0 | No |
| Calibration drift detected | ≥ ceil(0.5 × included_bins) bins pass | No |
| **Not calibrated** | **Fewer than 5/10 (or proportional) bins pass** | **Yes** |

With 2 bins included (8 excluded for n < 30), the proportional thresholds were:

```
strong_threshold     = ceil(0.9 × 2) = 2
acceptable_threshold = ceil(0.8 × 2) = 2
drift_threshold      = ceil(0.5 × 2) = 1
```

Pass count: **0 of 2 included bins.** Below all four thresholds, including the drift threshold of 1. The outcome is **"Not calibrated."**

---

## Result Detail

### Sample summary

| Field | Value |
|---|---|
| Model | `distilbert-base-uncased-finetuned-sst-2-english` |
| Model revision (HF commit) | `714eb0fa89d2f80546fda750413ed43d93601a13` |
| Test data | SST-2 validation split |
| Test data SHA-256 | `a0b4a680efac87830814939fea80664e23e0208a0db801472888a9672588376d` |
| Examples scored | 872 |
| Base rate (observed positive) | 50.92% |

### Aggregate metrics

| Metric | Value | Interpretation |
|---|---|---|
| Accuracy (auxiliary) | **0.9106** | 91.06% top-class agreement with labels (matches model card 91.3%) |
| Brier score | **0.0834** | Low absolute squared error; predictions are sharp |
| Brier climatology | 0.2499 | Brier score of always predicting the base rate |
| **Brier skill score** | **+0.6664** | Strongly positive; predictions are far better than base-rate |
| Expected Calibration Error (ECE) | **0.0720** | 7.2 percentage points average gap between predicted and observed |
| Maximum Calibration Error (MCE) | **0.0873** | 8.7 percentage points worst-bin gap |

### Per-bin reliability table

| Bin | Range | n | Mean predicted | Observed freq | Wilson 95% CI | Pass |
|---:|---|---:|---:|---:|---|:---:|
| 0 | [0.00, 0.10) | 392 | 0.0065 | 0.0612 | [0.0415, 0.0895] | **fail** |
| 1 | [0.10, 0.20) | 7 | — | — | — | excluded (n < 30) |
| 2 | [0.20, 0.30) | 4 | — | — | — | excluded |
| 3 | [0.30, 0.40) | 6 | — | — | — | excluded |
| 4 | [0.40, 0.50) | 3 | — | — | — | excluded |
| 5 | [0.50, 0.60) | 2 | — | — | — | excluded |
| 6 | [0.60, 0.70) | 3 | — | — | — | excluded |
| 7 | [0.70, 0.80) | 7 | — | — | — | excluded |
| 8 | [0.80, 0.90) | 8 | — | — | — | excluded |
| 9 | [0.90, 1.00] | 440 | 0.9964 | 0.9091 | [0.8786, 0.9325] | **fail** |

The two failing bins fail in the same direction: the bin's mean predicted probability sits *outside* the Wilson CI of the observed frequency, in the direction of greater confidence than the data supports.

- Bin 0: predicted 0.0065 vs Wilson lower bound 0.0415 → **3.5 pp below the floor of plausible.**
- Bin 9: predicted 0.9964 vs Wilson upper bound 0.9325 → **6.4 pp above the ceiling of plausible.**

---

## Diagnostic Reading

### The bimodal distribution

832 of 872 predictions (95.4%) fall into the two extreme bins. Only 40 predictions across the remaining 8 bins span the [0.10, 0.90) interior. The model rarely produces "uncertain" outputs; it commits, and it commits hard.

This is the empirical signature of a softmax classifier that has been fine-tuned to maximize cross-entropy on a clean, balanced training set: the model learns to drive its logits to large magnitudes whenever the correct class is identifiable, even when the underlying inferential confidence isn't actually that strong. A shallow probabilistic interpretation of "the model says 99.6%" overinterprets what the architecture actually optimized for.

### The accuracy/calibration contradiction

The contradiction surfaced by this audit is the central finding:

| Question | Answer | Source |
|---|---|---|
| Does the model classify correctly most of the time? | Yes (91%) | Auxiliary accuracy |
| Are the model's predictions much better than chance? | Yes (BSS +0.67) | Brier skill score |
| Are the model's predicted probabilities reliable as probabilities? | **No** | Pre-registered calibration test |

For applications that use only the predicted *class* (argmax), the model is fit. For applications that consume the predicted *probability* and threshold on it, propagate it into downstream uncertainty calculations, or use it to determine when to abstain or escalate, the model's outputs systematically misrepresent the actual reliability. A user setting a threshold of 0.95 expecting 95% precision will instead get something closer to 91%; a user setting a threshold of 0.05 expecting 5% false-positive risk will instead see ~6.1%.

### What this implies about the deployment context

The HuggingFace model card for `distilbert-base-uncased-finetuned-sst-2-english` reports accuracy and does not address calibration. Most users downloading this model implicitly rely on the published accuracy. This audit demonstrates that a probabilistic interpretation of the model's outputs is not supported by the same data the accuracy claim is based on. The two claims point at different downstream use-cases.

This is not a flaw in the model relative to its design; it is a flaw in the implicit claim that probabilities mean what they appear to mean.

---

## What This Test Does and Does Not Falsify

### Falsified

- The pre-registered calibration claim: that ≥ 8 of 10 bins pass the Wilson criterion AND BSS > 0. **Falsified** at 0 of 2 included bins passing.
- The implicit assumption that this model's predicted probabilities are reliable as probabilities. **Falsified** under the registered protocol.

### Not falsified

- The model's accuracy on SST-2 validation (91.1%, matching public claims).
- The model's Brier skill score (strongly positive at +0.67 — the predictions are far better than the base rate, even if not well-calibrated).
- The model's fitness for argmax-based classification.
- The model's behavior on out-of-distribution data (not in scope for v1).
- Any claim that a re-calibration layer (Platt scaling, isotonic regression, temperature scaling) could not fix this. Such a v2 test would be useful and is straightforward to design.

### What this case study demonstrates about the methodology

This is the first executed application of the AI calibration verification methodology productized from the verification + falsification engine in the `dynametrix` repository. The audit:

- Was pre-registered with all decision criteria locked before any prediction was computed.
- Was executed under cryptographic discipline: data SHA-256 verified at runtime, model revision pinned to a HuggingFace commit hash, script frozen at git commit `e6f6013`, outputs committed at `2f8bb9e` before this result document was drafted.
- Produced a falsifying outcome on a widely-used public model under conditions that any third party can reproduce by checking out commit `e6f6013`, downloading the same model revision, and running the script.
- Surfaced a finding that pure accuracy testing would miss.

---

## Implications for Users of the Audited Model

If you are using `distilbert-base-uncased-finetuned-sst-2-english` and your application:

- Uses only the **predicted class** (argmax of the two logits) for downstream decisions: this audit does not contraindicate your usage. Accuracy is as advertised.
- Uses the **predicted probability** as a decision threshold (e.g., "act only if confidence > 0.9"): the audit warns that the threshold's actual operating point differs from its nominal value by 6–8 percentage points at the extremes. Empirical re-calibration on your own validation data is recommended.
- Uses the **predicted probability** as input to downstream uncertainty propagation (e.g., Bayesian aggregation, ensemble weighting): the propagated uncertainties are not on the scale they appear to be on. Re-calibration is recommended.

A v2 audit could test whether common re-calibration techniques (temperature scaling, Platt scaling, isotonic regression) restore calibration on this model under the same protocol. That would be a separately pre-registered test.

---

## Implementation Observations

Two methodological observations recorded for transparency:

### 1. Bin-exclusion rule was load-bearing

8 of 10 bins fell below the n < 30 threshold and were excluded from the pass-count statistic per pre-reg Section 6.1. Without proportional thresholds, a naive "≥ 8 of 10 bins" rule would have been undefined when only 2 bins are eligible. The proportional-threshold logic baked into the pre-registration handled this cleanly: with 2 included bins, both must pass for "Calibrated (acceptable)" and 0 of 2 falls below even the drift threshold. This is the kind of edge case worth ensuring is in the template for future engagements — extreme prediction distributions are common in classifier audits.

### 2. Inference environment and lock-to-run gap

The pre-registration's Section 4.3 records the inference environment as auxiliary information rather than as part of the calibration claim. The lock commit `e6f6013` was made on 2026-05-04. Resolving Windows-side torch DLL configuration (numpy/MKL/OpenMP/fbgemm interactions in a Miniforge conda env) took two calendar days; the actual calibration was executed on 2026-05-06. This gap does not violate the pre-registration's lock-in-advance discipline — no methodology was modified, no data was inspected, no decision threshold was adjusted between lock and run — but it is worth recording for transparency. A v2 productized engagement should include in its setup checklist a "verify torch loads cleanly with numpy" test before lock commit, to avoid this kind of gap on future runs.

Recorded environment values for this run:

| Field | Value |
|---|---|
| Python | 3.11.x (conda env `spinphase_gw` on Windows) |
| torch | 2.10.0 (installed via `conda install -c pytorch pytorch cpuonly`; the conda-forge build to coexist with conda's MKL) |
| transformers | 5.8.0 |
| datasets | 4.8.5 |
| huggingface-hub | 1.13.0 |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` (set during execution to allow OpenMP runtime coexistence) |

Multiple iterations of torch installation (pip 2.11.0 with `WinError 127`, pip 2.5.1 with numpy/torch DLL conflict, conda-forge attempt, pytorch-channel 2.10.0 succeeded) were tried before achieving a working DLL configuration on this machine. Per pre-reg Section 4.3, the environment is recorded for reproducibility but does not constitute the subject of the calibration claim. The numerical results from torch 2.10.0 inference would be expected to match torch 2.5.1 inference for this model and these inputs to within float32 precision.

---

## Lock and Provenance

| Item | Reference |
|---|---|
| Pre-registration document | `case_studies/distilbert_sst2/PRE_REGISTRATION_DISTILBERT_SST2_v1.md` |
| Pre-registration / pipeline lock commit | git `e6f6013` (2026-05-04) |
| Analysis script | `case_studies/distilbert_sst2/distilbert_sst2_calibration.py` (frozen at `e6f6013`) |
| Test data | `case_studies/distilbert_sst2/sst2_validation.csv` (SHA-256 `a0b4a680…`) |
| Model revision (HF commit hash) | `714eb0fa89d2f80546fda750413ed43d93601a13` |
| Per-example predictions | `case_studies/distilbert_sst2/predictions.csv` (committed at `2f8bb9e`, 2026-05-06) |
| Per-bin reliability scores | `case_studies/distilbert_sst2/calibration_scores.csv` (committed at `2f8bb9e`) |
| Aggregate calibration summary | `case_studies/distilbert_sst2/calibration_summary.json` (committed at `2f8bb9e`) |
| This result document commit | (recorded after committing) |

Per pre-registration Section 11, the methodology was bound at lock commit `e6f6013` before any inference was run; the score vector was committed at `2f8bb9e` before this result document was drafted; the test outcome is published irrespective of whether it is favorable to the audited model.

---

*End of DistilBERT SST-2 Calibration Verification v1 Outcome.*