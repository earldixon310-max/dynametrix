# DistilBERT SST-2 Calibration Verification — Pre-Registration v1

**Identifier:** `distilbert-sst2-calibration-v1`
**Lock date:** 2026-05-04
**Customer:** Earl Dixon (self-audit for public demonstration purposes; no commercial relationship)
**Auditor:** Earl Dixon
**Status:** Locked. Any change to the items below constitutes a methodology version bump and requires a new pre-registration document.

> **Engagement type:** Public demonstration audit. The customer and auditor roles are filled by the same party for the purpose of demonstrating the calibration verification methodology end-to-end on a publicly accessible model. The result is published as a case study irrespective of outcome. No commercial relationship, no confidentiality redactions, full transparency end-to-end.

---

## 1. Purpose

This document fixes, in advance of computation, the methodology by which the calibration of `distilbert-base-uncased-finetuned-sst-2-english` will be evaluated against the SST-2 validation split. The test answers a single pre-specified question: do the model's predicted positive-class probabilities match observed positive-class frequencies on the held-out evaluation data, under the criteria locked below?

This is **not** a test of the model's accuracy, fitness for any specific sentiment-analysis purpose, robustness to adversarial inputs, fairness, or production suitability. It is a calibration test only — the narrow technical question of whether predicted probabilities are reliable as probabilities.

The lock-in-advance discipline of this document is the methodological contribution. Every parameter, threshold, and decision criterion below is fixed before any prediction is generated.

---

## 2. The Claim Under Test

### 2.1 Model

| Field | Value |
|---|---|
| Model name | `distilbert-base-uncased-finetuned-sst-2-english` |
| Source | HuggingFace Hub |
| Revision | `714eb0fa89d2f80546fda750413ed43d93601a13` (HuggingFace Hub commit hash, pinned at lock) |
| Training data description | Fine-tuned by HuggingFace on SST-2 training split (~67k examples), starting from DistilBERT base pretrained on BookCorpus + Wikipedia. |
| Output type | Binary classifier (NEGATIVE = label 0, POSITIVE = label 1) |
| Output range | Probability in [0, 1] of the POSITIVE class, computed as softmax(logits)[1] |
| Inference parameters | No temperature scaling, no thresholding. Default tokenization (truncation=True, max_length=512). |

### 2.2 Calibration claim being tested

> **For each of 10 equal-width reliability bins on [0, 1], the Wilson 95% confidence interval is computed for the observed positive-class frequency in that bin. A bin "passes" if the bin's mean predicted probability falls within that confidence interval. The model is calibrated under this audit if at least 8 of 10 bins pass; AND the Brier skill score is positive against a base-rate climatology baseline.**

This is the registered claim. Failure to meet this claim produces a "calibration drift detected" or "not calibrated" outcome (see Section 6). The framing — Wilson CI built around the observed frequency, with the predicted probability tested against it — is the standard direction for calibration testing under finite samples and is precisely the question "given the bin's observed positive rate and sample size, is the model's predicted probability statistically consistent with that observation?"

---

## 3. Test Data

### 3.1 Source

| Field | Value |
|---|---|
| Dataset | GLUE / SST-2 validation split |
| Source | HuggingFace Datasets (`datasets.load_dataset("glue", "sst2", split="validation")`) |
| Provenance | Public benchmark; held out from the model's fine-tuning training split. The model was fine-tuned on the SST-2 *training* split (~67k examples); the *validation* split (872 examples) was not used for fine-tuning. |
| Size | 872 examples |
| Hash (SHA-256) of test data CSV | `a0b4a680efac87830814939fea80664e23e0208a0db801472888a9672588376d` |
| Class distribution | Reported in result document (approximately balanced; ~50% positive) |

### 3.2 Held-out integrity

The auditor attests that:

- The SST-2 validation split is the public benchmark validation split and is distinct from the SST-2 training split used for fine-tuning. This audit treats the validation split as the registered evaluation set, while acknowledging that widely-used public benchmark models may have been indirectly selected or optimized based on validation-set performance during their development. The validation split's status as fully held-out from any signal about the model's training process is therefore not asserted; only that it is distinct from the explicit training partition.
- The validation data is fixed at the SHA hash recorded above (computed once at materialization time and locked in this commit) and will not be modified before execution.

Because this is a public demonstration audit on a public model and a public dataset, the data hash and the model revision are verifiable by any third party who downloads the same artifacts and recomputes the hashes.

### 3.3 Subgroup analysis

No subgroup analysis is in scope for v1. The SST-2 validation set is a single-domain corpus of movie review sentiment with no annotated subgroups. A v2 might extend to OOD test sets (Amazon reviews, Yelp reviews) for distribution-shift calibration analysis.

---

## 4. Inference Pipeline

### 4.1 Pipeline specification

The model is queried for prediction on each test example via the inference code at `case_studies/distilbert_sst2/distilbert_sst2_calibration.py`. The inference code is frozen at git commit [TO BE FILLED AT COMMIT] and is not modified between this commit and the recording of all predictions.

### 4.2 Output processing

| Field | Value |
|---|---|
| How predictions are extracted | For each input sentence, tokenize, forward-pass, apply softmax to the 2-dimensional logits, and take the probability of class label 1 (POSITIVE) as the model's prediction. |
| Any thresholding or transformation | None. Raw softmax output is the predicted probability. |
| Numerical precision | float32 inference, float64 calibration computation. |

### 4.3 Inference environment

| Field | Value |
|---|---|
| Hardware | CPU (Intel x86_64 on the local Windows machine in conda env `spinphase_gw`) |
| Library versions | `transformers`, `torch`, `datasets` — pinned in `case_studies/distilbert_sst2/requirements.txt` at lock commit |
| Random seed | Not applicable (model inference is deterministic for fixed inputs) |
| Batch size | 1 (sentence-by-sentence; speed is acceptable for 872 examples) |

The inference environment is recorded for reproducibility. It is not the subject of the calibration claim.

---

## 5. Calibration Metrics

### 5.1 Reliability bins

Predictions are partitioned into K = 10 equal-width bins on the predicted-positive-class-probability axis: `[0.0, 0.1)`, `[0.1, 0.2)`, …, `[0.9, 1.0]` (the last bin is closed on both sides).

For each bin:

- Number of examples (n)
- Mean predicted probability
- Observed frequency of the positive class (label = 1)
- Wilson 95% confidence interval on the observed frequency

Bins with n < 30 examples are reported but excluded from the bin-pass-count statistic per Section 6.1.

### 5.2 Aggregate metrics

- **Brier score:** `mean((predicted_prob - actual_label)^2)` across all 872 examples.
- **Brier skill score (BSS) against base-rate climatology:** `1 - (Brier_model / Brier_climatology)`, where `Brier_climatology = mean((p_base - actual_label)^2)` and `p_base` is the observed positive-class base rate in the validation set.
- **Expected Calibration Error (ECE):** `sum_i (n_i / N) * |bin_mean_pred_i - bin_observed_freq_i|` across non-empty bins. Reported but not used in the primary decision criteria.
- **Maximum Calibration Error (MCE):** `max_i |bin_mean_pred_i - bin_observed_freq_i|` across bins with n ≥ 30. Reported.

---

## 6. Pre-Registered Decision Criteria

### 6.1 Primary decision

The model's calibration is classified into one of four pre-registered outcomes:

| Outcome | Criterion |
|---|---|
| **Calibrated (strong)** | At least 9 of 10 bins (excluding bins with n < 30) pass the Wilson criterion (the bin's mean predicted probability falls within the Wilson 95% CI of the bin's observed positive-class frequency), AND BSS > 0. |
| **Calibrated (acceptable)** | At least 8 of 10 bins pass the Wilson criterion, AND BSS > 0. |
| **Calibration drift detected** | Fewer than 8 of 10 bins pass the Wilson criterion, OR BSS ≤ 0. |
| **Not calibrated** | Fewer than 5 of 10 bins pass the Wilson criterion. |

If a bin has n < 30, it is excluded from the count (denominator becomes 10 minus the number of excluded bins). The decision thresholds are then applied proportionally — e.g., if 2 bins are excluded, "Calibrated (acceptable)" requires ≥ 6 of the remaining 8 bins to meet the Wilson criterion (8/10 → 6.4 → ceil to 7; documented as ceil(0.8 × included_bins)).

For clarity, the exact decision rule with bin exclusions:

```
included_bins = K - excluded_bins
strong_threshold = ceil(0.9 * included_bins)
acceptable_threshold = ceil(0.8 * included_bins)
drift_threshold = ceil(0.5 * included_bins)

if pass_count >= strong_threshold and BSS > 0:
    outcome = "Calibrated (strong)"
elif pass_count >= acceptable_threshold and BSS > 0:
    outcome = "Calibrated (acceptable)"
elif pass_count >= drift_threshold:
    outcome = "Calibration drift detected"
else:
    outcome = "Not calibrated"
```

### 6.2 Secondary outcome (auxiliary)

The unweighted mean of `|bin_observed - bin_predicted|` across qualifying bins is reported as a single calibration drift magnitude. This is reported alongside the primary outcome but does not modify it.

---

## 7. Sanity Checks (auxiliary)

The following are reported alongside the primary decision but do not modify it:

### 7.1 Class balance

Reported actual base rate (observed proportion of label = 1 in the 872-example validation set). Cross-checked against the SST-2 metadata. Discrepancy > 5pp is flagged.

### 7.2 Prediction distribution

Histogram of predicted positive-class probabilities across the 872 examples, with mean, median, and percentiles. If > 90% of predictions fall in a single bin, the calibration test's statistical power is reduced and this is noted in the result document.

### 7.3 Per-class accuracy (auxiliary, not part of calibration)

Top-line accuracy (fraction of predictions where the argmax class matches the label) is reported as auxiliary context, since accuracy is the most common claim a reader will look for. It is not part of the calibration outcome.

### 7.4 Logit magnitude distribution

Mean absolute logit value reported. Highly saturated logits (mean |logit| > 8) suggest the model is confidence-extreme and may be prone to miscalibration at the bin extremes.

---

## 8. What This Test Does Not Claim

Registering this test makes none of the following claims:

- That `distilbert-base-uncased-finetuned-sst-2-english` is accurate or fit for any specific sentiment-analysis purpose.
- That the model's calibration on SST-2 validation transfers to other sentiment data (Amazon reviews, tweets, news, etc.). A v2 audit on out-of-distribution data would be required.
- That the model is robust to adversarial inputs or distribution shift.
- That the model is fair or unbiased across populations not enumerated here.
- That a "calibrated" outcome implies regulatory approval, audit clearance, or compliance with any specific framework.

A "calibrated" outcome means and only means: under the SST-2 validation set and the decision criteria locked above, the model's predicted positive-class probabilities matched observed positive-class frequencies within the registered tolerances.

---

## 9. Test Logistics

### 9.1 Pre-test artifacts (committed before any prediction is computed)

The following are committed to git before execution:

- This pre-registration document.
- The inference and analysis script `distilbert_sst2_calibration.py` at the frozen commit hash.
- The materialized SST-2 validation CSV (`sst2_validation.csv`) and its SHA-256 hash file (`sst2_validation_sha256.txt`).
- A pinned `requirements.txt` listing transformers, torch, datasets versions.

### 9.2 Test execution

The auditor runs the frozen analysis script once. All 872 predictions are computed, all calibration metrics are calculated, and the results are written to `calibration_scores.csv` and `calibration_summary.json` before any inspection of the calibration outcome. Re-running for verification is permitted; revising outcomes is not.

### 9.3 Result reporting

The locked result document `RESULT_DISTILBERT_SST2_v1_<date>.md` is drafted and committed by the auditor immediately after the calibration computation completes and is never modified post-commit. Because this is a public demonstration audit, no confidentiality redactions are applied — the full result is published.

### 9.4 Disclosure of failure

If the test produces a "calibration drift detected" or "not calibrated" outcome, the result document records this outcome and is published unchanged. The audit is run end-to-end regardless of which way the result lands.

---

## 10. Lock and Provenance

This document is committed to git alongside the analysis code, requirements file, materialized test data, and data hash file in a single lock commit.

| Item | Reference |
|---|---|
| Pre-registration commit hash | [TO BE RECORDED IN RESULT DOCUMENT] |
| Analysis script commit hash | (same — single lock commit) |
| Test data file | `case_studies/distilbert_sst2/sst2_validation.csv` |
| Test data SHA-256 | `a0b4a680efac87830814939fea80664e23e0208a0db801472888a9672588376d` |
| Model revision | `714eb0fa89d2f80546fda750413ed43d93601a13` |

---

## 11. Pre-Test Status (as of lock date)

Recorded for context (not part of the test):

- This is the first public case study of the AI calibration verification methodology productized from the verification + falsification engine demonstrated in `dynametrix` repository over April–May 2026.
- The methodology was previously demonstrated on five pre-registered tests across two scientific domains: weather forecasting (`PRE_REGISTRATION_v1`, `v2`, `v3a`) and gravitational-wave detection (`PRE_REGISTRATION_GW_v1`, `PRE_REGISTRATION_GW_QUIETWELL_v1`). All five produced clean falsifying outcomes; all five result documents are committed to the same git history.
- No prior calibration analysis of `distilbert-base-uncased-finetuned-sst-2-english` is known to the auditor at lock time. The HuggingFace model card reports accuracy (91.3% on SST-2 validation) but does not report calibration metrics.
- The model is in widespread public production use on HuggingFace Hub. The Hub-reported download count varies; the snapshot value at lock date will be recorded in the result document if material to interpretation.

---

*End of DistilBERT SST-2 Calibration Verification v1 Pre-Registration.*