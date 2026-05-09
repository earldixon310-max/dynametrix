# Toxic-BERT Calibration Verification — Pre-Registration v1

**Identifier:** `toxic-bert-calibration-v1`
**Lock date:** 2026-05-06
**Customer:** Earl Dixon (self-audit for public demonstration purposes; no commercial relationship)
**Auditor:** Earl Dixon
**Status:** Locked at commit `1cca21373220da912974b0d62b3d40b7a8b6d11e`. Any change to the items below constitutes a methodology version bump and requires a new pre-registration document.

> **Engagement type:** Public demonstration audit. The customer and auditor roles are filled by the same party for the purpose of demonstrating the calibration verification methodology end-to-end on a publicly accessible toxicity-detection model. The result is published as a case study irrespective of outcome. No commercial relationship, no confidentiality redactions, full transparency end-to-end.

---

## 1. Purpose

This document fixes, in advance of computation, the methodology by which the calibration of `unitary/toxic-bert` will be evaluated against a held-out subset of the Civil Comments dataset. The test answers a single pre-specified question: do the model's predicted probabilities of the *toxicity* label match observed *toxicity* frequencies on the held-out evaluation data, under the criteria locked below?

This is **not** a test of the model's overall accuracy on toxicity classification, fairness across demographic subgroups, fitness for any specific content-moderation deployment, or robustness to adversarial inputs. It is a calibration test only — the narrow technical question of whether predicted probabilities are reliable as probabilities for the specific positive class (toxicity = True).

The lock-in-advance discipline of this document is the methodological contribution. Every parameter, threshold, and decision criterion below is fixed before any prediction is generated.

This is the second public case study in a series demonstrating the AI calibration verification methodology productized from the verification + falsification engine in [github.com/earldixon310-max/dynametrix](https://github.com/earldixon310-max/dynametrix). The first was `distilbert-sst2-calibration-v1` ([result](https://github.com/earldixon310-max/dynametrix/blob/master/docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md)).

---

## 2. The Claim Under Test

### 2.1 Model

| Field | Value |
|---|---|
| Model name | `unitary/toxic-bert` |
| Source | HuggingFace Hub |
| Revision | `4d6c22e74ba2fdd26bc4f7238f50766b045a0d94` (HuggingFace Hub commit hash, pinned at lock) |
| Training data description | Fine-tuned by Unitary on the Civil Comments dataset (the Jigsaw Unintended Bias in Toxicity Classification challenge data), starting from `bert-base-uncased`. The model produces 6 separate sigmoid outputs corresponding to: toxic, severe_toxic, obscene, threat, insult, identity_hate. |
| Output type | Multi-head binary classifier; for this audit, the **toxic** head is the subject of evaluation. |
| Output range | Probability in [0, 1] of the *toxicity* label, computed as sigmoid(logits)[toxic_idx] |
| Inference parameters | Default tokenization (truncation=True, max_length=512). No threshold applied; raw sigmoid output is the predicted probability. |

### 2.2 Calibration claim being tested

> **For each of 10 equal-width reliability bins on [0, 1], the Wilson 95% confidence interval is computed for the observed toxic-class frequency in that bin. A bin "passes" if the bin's mean predicted probability falls within that confidence interval. The model is calibrated under this audit if at least 8 of 10 bins pass; AND the Brier skill score is positive against a base-rate climatology baseline.**

This is the registered claim. Failure to meet this claim produces a "calibration drift detected" or "not calibrated" outcome (see Section 6). The framing — Wilson CI built around the observed frequency, with the predicted probability tested against it — is the standard direction for calibration testing under finite samples and is precisely the question "given the bin's observed positive rate and sample size, is the model's predicted probability statistically consistent with that observation?"

The Wilson criterion and the BSS clause are identical to those used in `distilbert-sst2-calibration-v1`. This audit thereby produces a result directly comparable to the prior case study.

---

## 3. Test Data

### 3.1 Source

| Field | Value |
|---|---|
| Dataset | Civil Comments (Jigsaw Unintended Bias in Toxicity Classification), validation split |
| Source | HuggingFace Datasets (`datasets.load_dataset("google/civil_comments", split="validation")`) |
| Provenance | Public benchmark dataset, released by Jigsaw/Google under research-license terms permitting redistribution and derivative use. |
| Total validation size | 97,320 examples (per Jigsaw release) |
| **Subsample for this audit** | 5,000 examples, deterministically selected by random seed `150914` (matching the seed convention from prior pre-registrations in this repository). The subsample is drawn from the validation split, sorted by row index after shuffle, and saved as a CSV at materialization time. |
| Hash (SHA-256) of subsample CSV | `647436da227d2231822a3d57fd60c7a153b63dfba97c290655b9f8838b71dc33` |
| Class distribution | Reported in result document; the `toxic` label has approximately 8% positive rate in Civil Comments overall. |

The 5,000-example subsample is chosen to balance statistical power (sufficient to populate ≥30 examples in most bins) against computational cost (~5,000 inference calls vs. 97,320). The subsampling is fixed at a registered seed and the resulting CSV is hashed; reproducibility of the subsample is verifiable by any third party who runs the same seed against the same dataset version.

### 3.2 Held-out integrity

The auditor attests that:

- The Civil Comments validation split is the public benchmark validation split and is distinct from the Civil Comments training split used for fine-tuning. This audit treats the validation split as the registered evaluation set, while acknowledging that widely-used public benchmark models may have been indirectly selected or optimized based on validation-set performance during their development. The validation split's status as fully held-out from any signal about the model's training process is therefore not asserted; only that it is distinct from the explicit training partition.
- The subsample CSV is fixed at the SHA hash recorded above (computed once at materialization time and locked in this commit) and will not be modified before execution.
- The subsample selection seed (`150914`) is recorded in this document and embedded in the analysis script. Any third party can reproduce the subsample by running the same selection logic against the same dataset version.

### 3.3 Subgroup analysis

No subgroup analysis is in scope for v1. The Civil Comments dataset includes identity labels (e.g., `male`, `female`, `christian`, `muslim`, `jewish`, `black`, `white`, `lgbtq`, etc.) that would support demographic-stratified calibration analysis, but a fairness/subgroup audit is a separate methodological class and is deferred to a potential v2 pre-registration. v1 scope is limited to overall calibration of the *toxic* label.

This is a deliberate scoping choice. Subgroup calibration of toxicity classifiers is politically charged and requires its own pre-registered protocol with explicit fairness criteria, multiple-comparison correction across subgroups, and independently locked decision rules. Mixing it into a calibration audit would dilute both questions.

---

## 4. Inference Pipeline

### 4.1 Pipeline specification

The model is queried for prediction on each test example via the inference code at `case_studies/toxic_bert/toxic_bert_calibration.py`. The inference code is frozen at git commit [TO BE FILLED AT COMMIT] and is not modified between this commit and the recording of all predictions.

### 4.2 Output processing

| Field | Value |
|---|---|
| How predictions are extracted | For each input comment, tokenize, forward-pass, apply sigmoid to the logit corresponding to the `toxic` label, and take that sigmoid output as the model's predicted probability of toxicity. |
| Any thresholding or transformation | None. Raw sigmoid output of the `toxic` head is the predicted probability. |
| Numerical precision | float32 inference, float64 calibration computation. |
| Ground-truth threshold | Civil Comments labels are continuous in [0, 1] (fraction of human raters labeling the comment as toxic). Per the dataset's standard convention, a comment is considered "toxic" (positive class = 1) if its ground-truth toxicity score is ≥ 0.5; otherwise non-toxic (negative class = 0). |

### 4.3 Inference environment

| Field | Value |
|---|---|
| Hardware | CPU (Intel x86_64 on the local Windows machine; same conda env as `distilbert-sst2-calibration-v1`) |
| Library versions | `transformers`, `torch`, `datasets` — pinned in `case_studies/toxic_bert/requirements.txt` at lock commit |
| Random seed (subsample selection) | `150914` |
| Random seed (model inference) | Not applicable (forward pass is deterministic for fixed inputs) |
| Batch size | 1 (sentence-by-sentence; speed is acceptable for 5,000 examples) |

---

## 5. Calibration Metrics

### 5.1 Reliability bins

Predictions are partitioned into K = 10 equal-width bins on the predicted-toxicity-probability axis: `[0.0, 0.1)`, `[0.1, 0.2)`, …, `[0.9, 1.0]` (the last bin is closed on both sides).

For each bin:

- Number of examples (n)
- Mean predicted probability of toxicity
- Observed frequency of the toxic class (label = 1, where label is the binarized ground-truth toxicity score)
- Wilson 95% confidence interval on the observed frequency

Bins with n < 30 examples are reported but excluded from the bin-pass-count statistic per Section 6.1.

### 5.2 Aggregate metrics

- **Brier score:** `mean((predicted_prob - actual_label)^2)` across all 5,000 examples.
- **Brier skill score (BSS) against base-rate climatology:** `1 - (Brier_model / Brier_climatology)`, where `Brier_climatology = mean((p_base - actual_label)^2)` and `p_base` is the observed positive-class base rate in the subsample.
- **Expected Calibration Error (ECE):** `sum_i (n_i / N) * |bin_mean_pred_i - bin_observed_freq_i|` across non-empty bins. Reported but not used in the primary decision criteria.
- **Maximum Calibration Error (MCE):** `max_i |bin_mean_pred_i - bin_observed_freq_i|` across bins with n ≥ 30. Reported.

---

## 6. Pre-Registered Decision Criteria

### 6.1 Primary decision

The model's calibration is classified into one of four pre-registered outcomes, identical in structure to `distilbert-sst2-calibration-v1`:

| Outcome | Criterion |
|---|---|
| **Calibrated (strong)** | At least 9 of 10 bins (excluding bins with n < 30) pass the Wilson criterion (the bin's mean predicted probability falls within the Wilson 95% CI of the bin's observed toxic-class frequency), AND BSS > 0. |
| **Calibrated (acceptable)** | At least 8 of 10 bins pass the Wilson criterion, AND BSS > 0. |
| **Calibration drift detected** | Fewer than 8 of 10 bins pass the Wilson criterion, OR BSS ≤ 0. |
| **Not calibrated** | Fewer than 5 of 10 bins pass the Wilson criterion. |

If a bin has n < 30, it is excluded from the count. Decision thresholds are then applied proportionally:

```
included_bins = K - excluded_bins
strong_threshold = ceil(0.9 * included_bins)
acceptable_threshold = ceil(0.8 * included_bins)
drift_threshold = ceil(0.5 * included_bins)
```

### 6.2 Secondary outcome (auxiliary)

The unweighted mean of `|bin_observed - bin_predicted|` across qualifying bins is reported as a single calibration drift magnitude. This is reported alongside the primary outcome but does not modify it.

---

## 7. Sanity Checks (auxiliary)

The following are reported alongside the primary decision but do not modify it:

### 7.1 Class balance

Reported actual toxic-class base rate (proportion of subsample where ground-truth toxicity score ≥ 0.5). Cross-checked against the Civil Comments published metadata. Discrepancy > 5pp is flagged.

### 7.2 Prediction distribution

Histogram of predicted toxicity probabilities across the 5,000 examples, with mean, median, and percentiles. Following the pattern observed in `distilbert-sst2-calibration-v1`, sigmoid-output classifiers fine-tuned on cross-entropy often exhibit bimodal prediction distributions; this is reported and discussed in the result document if observed.

### 7.3 Per-class accuracy (auxiliary, not part of calibration)

Top-class accuracy at threshold 0.5 (fraction of predictions where the binarized predicted output matches the binarized label) is reported as auxiliary context. It is not part of the calibration outcome.

### 7.4 Logit magnitude distribution

Mean absolute logit value reported for the `toxic` head. Highly saturated logits (mean |logit| > 8) suggest the model is confidence-extreme and may be prone to miscalibration at the bin extremes.

---

## 8. What This Test Does Not Claim

Registering this test makes none of the following claims:

- That `unitary/toxic-bert` is accurate or fit for any specific content-moderation purpose.
- That the model's calibration on Civil Comments validation transfers to other text distributions (social media, news comments, product reviews, etc.). A v2 audit on out-of-distribution data (e.g., HateCheck or HateXplain) would be required.
- That the model is fair or unbiased across demographic subgroups. Subgroup calibration analysis is explicitly out of scope (Section 3.3).
- That a "calibrated" outcome implies the model is safe to deploy for content moderation.
- That a "not calibrated" outcome implies the model is harmful or that its authors have erred. Most toxicity classifier model cards make no calibration claim; this audit tests an *implicit assumption* that probabilistic outputs from such classifiers are reliable as probabilities.

A "calibrated" outcome means and only means: under the Civil Comments validation subsample at seed `150914` and the decision criteria locked above, the model's predicted toxicity probabilities matched observed toxic-class frequencies within the registered tolerances.

---

## 8.1 Public-Audit Attestation

This audit is conducted on a publicly licensed model (`unitary/toxic-bert`, Apache 2.0 license per its HuggingFace model card) and publicly licensed test data (Civil Comments, released by Jigsaw/Google under research-license terms permitting redistribution and derivative use). No commercial relationship exists between the auditor and the model authors (Unitary Ltd.). The audit is published under the principle that independent third-party evaluation of public AI systems is legitimate research, consistent with established practice across the AI evaluation field.

Findings in the result document are framed as factual measurements under the registered protocol. They are not framed as judgments of the model's authors, the model's commercial fitness, or the model's suitability for any specific deployment context. The methodology and the result document are released so that any third party may inspect, reproduce, and critique the findings.

The model authors will be notified of publication via the model's HuggingFace Hub discussion thread following result document commit, as a courtesy and not as a precondition. Author response, if any, may be published as an addendum to the result document. The methodology lock is not affected by author response.

The auditor asserts:

- The model used is `unitary/toxic-bert` at the pinned revision recorded in Section 2.1, retrieved from the public HuggingFace Hub source, under the Apache 2.0 license documented on the model's public model card.
- The test data used is the Civil Comments validation split at the SHA-256 hash recorded in Section 3.1, retrieved from the public HuggingFace Datasets source, under Jigsaw/Google's published license terms.
- No proprietary or confidential information about the model's training, internal architecture, or non-public weights is used in the audit. The audit is conducted entirely from publicly available artifacts.

---

## 9. Test Logistics

### 9.1 Pre-test artifacts (committed before any prediction is computed)

The following are committed to git before execution:

- This pre-registration document.
- The inference and analysis script `toxic_bert_calibration.py` at the frozen commit hash.
- The materialized Civil Comments subsample CSV (`civil_comments_validation_subsample.csv`) and its SHA-256 hash file.
- A pinned `requirements.txt` listing transformers, torch, datasets versions.
- The pinned model revision file (`model_revision.txt`).

### 9.2 Test execution

The auditor runs the frozen analysis script once. All 5,000 predictions are computed, all calibration metrics are calculated, and the results are written to `calibration_scores.csv` and `calibration_summary.json` before any inspection of the calibration outcome. Re-runs for verification are permitted; revisions to outputs are not.

### 9.3 Result reporting

The locked result document `RESULT_TOXIC_BERT_v1_<date>.md` is drafted and committed by the auditor immediately after the calibration computation completes and is never modified post-commit. Because this is a public demonstration audit, no confidentiality redactions are applied — the full result is published.

### 9.4 Disclosure of failure

If the test produces a "calibration drift detected" or "not calibrated" outcome, the result document records this outcome and is published unchanged. The audit is run end-to-end regardless of which way the result lands.

---

## 10. Lock and Provenance

This document is committed to git alongside the analysis code, requirements file, materialized subsample data, and data hash file in a single lock commit.

| Item | Reference |
|---|---|
| Pre-registration commit hash | [TO BE RECORDED IN RESULT DOCUMENT] |
| Analysis script commit hash | (same — single lock commit) |
| Test data file | `case_studies/toxic_bert/civil_comments_validation_subsample.csv` |
| Test data SHA-256 | `647436da227d2231822a3d57fd60c7a153b63dfba97c290655b9f8838b71dc33` |
| Subsample selection seed | `150914` |
| Model revision | `4d6c22e74ba2fdd26bc4f7238f50766b045a0d94` |

---

## 11. Pre-Test Status (as of lock date)

Recorded for context (not part of the test):

- This is the second public case study in the AI calibration verification methodology series. The first was `distilbert-sst2-calibration-v1` ([result](https://github.com/earldixon310-max/dynametrix/blob/master/docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md)), which produced a "Not calibrated" outcome on the DistilBERT-SST-2 sentiment classifier and surfaced a bimodal-overconfidence pattern.
- The methodology was previously demonstrated on five pre-registered tests across two scientific domains: weather forecasting and gravitational-wave detection. All five produced clean falsifying outcomes; all five result documents are committed to the same git history.
- No prior calibration analysis of `unitary/toxic-bert` is known to the auditor at lock time. The model's HuggingFace model card reports overall AUC and accuracy metrics on Civil Comments test but does not report calibration metrics.
- The model is in widespread public use; download volume and dependent applications are documented on the HuggingFace Hub model card.
- A prediction worth recording at lock: based on the pattern observed in `distilbert-sst2-calibration-v1` (cross-entropy-trained sigmoid classifiers tend to be confident-extreme and produce miscalibrated probabilities at the bin extremes), the auditor's prior expectation is that this audit will also produce a "not calibrated" outcome with bimodal overconfidence. This expectation is recorded so that, if the audit instead produces a "calibrated" outcome, the surprise is itself an informative finding worth discussing in the result document. If the expectation holds, the consistency across two independent public audits strengthens the methodological generalization.

---

*End of Toxic-BERT Calibration Verification v1 Pre-Registration.*