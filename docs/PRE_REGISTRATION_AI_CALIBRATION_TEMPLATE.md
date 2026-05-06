# AI Model Calibration Verification — Pre-Registration Template v1

**Template version:** v1.0
**Purpose:** Sample pre-registration document for an independent calibration audit of a probabilistic AI/ML model. Customer and auditor jointly fill in the bracketed fields, sign, and commit the resulting document to git before any prediction is computed against the test data.

> **How to use this template.** Fields marked `[CUSTOMER FILLS]` are agreed during scoping and filled in before signing. Fields marked `[AUDITOR FILLS]` are filled by the auditor during methodology drafting. Sections without bracketed fields are fixed methodological language and should not be modified per engagement (modification constitutes a different methodology and would require a fresh template version).

---

# [CUSTOMER FILLS: Project name] Calibration Verification — Pre-Registration v[CUSTOMER FILLS: revision]

**Identifier:** `[CUSTOMER FILLS: short kebab-case identifier, e.g. acme-fraud-classifier-calibration-v1]`
**Lock date:** [AUDITOR FILLS: ISO date]
**Customer:** [CUSTOMER FILLS: organization name, team, primary contact]
**Auditor:** [AUDITOR FILLS: auditing party, primary contact]
**Status:** Locked. Any change to the items below constitutes a methodology version bump and requires a new pre-registration document.

---

## 1. Purpose

This document fixes, in advance of computation, the methodology by which the calibration of [CUSTOMER FILLS: model name and version] will be evaluated against [CUSTOMER FILLS: dataset name]. The test answers a single pre-specified question: do the model's predicted probabilities match observed frequencies in the held-out evaluation data, under the criteria locked below?

This is **not** a test of the model's accuracy, fitness for purpose, robustness, fairness, or production suitability. It is a calibration test — the narrow technical question of whether predicted probabilities are reliable as probabilities. Customers should commission separate evaluations for the other dimensions if needed.

The lock-in-advance discipline of this document is the entire methodological contribution. Every parameter, threshold, and decision criterion below is fixed before any prediction is generated against the test data. Once committed, this document is bound and not subject to revision.

---

## 2. The Claim Under Test

### 2.1 Model

| Field | Value |
|---|---|
| Model name | [CUSTOMER FILLS] |
| Version / commit hash | [CUSTOMER FILLS] |
| Training data description | [CUSTOMER FILLS: high level — what the model was trained on] |
| Output type | [CUSTOMER FILLS: binary classifier / multi-class / regression with probability] |
| Output range | [CUSTOMER FILLS: e.g., probability in [0, 1] of class POSITIVE] |
| Inference parameters | [CUSTOMER FILLS: temperature, top-k, threshold, etc., if any] |

### 2.2 Calibration claim being tested

> **[CUSTOMER FILLS: state the calibration claim in one sentence. Example: "The model's predicted probabilities of class POSITIVE are calibrated such that, across 10 equal-width reliability bins, the observed positive-class frequency falls within the Wilson 95% confidence interval of the bin's mean predicted probability for at least 8 of 10 bins."]**

The claim must be a falsifiable statement about the relationship between predicted probabilities and observed frequencies. Vague claims ("the model is well calibrated") cannot be tested under this protocol.

---

## 3. Test Data

### 3.1 Source

| Field | Value |
|---|---|
| Dataset | [CUSTOMER FILLS: name and version of test set] |
| Provenance | [CUSTOMER FILLS: held out from training? curated independently? both?] |
| Size | [CUSTOMER FILLS: total number of examples] |
| Hash (SHA-256) of the test data file | [AUDITOR FILLS: computed at lock time] |
| Class distribution / base rate | [CUSTOMER FILLS: e.g., 50% positive, 50% negative] |

### 3.2 Held-out integrity

The customer attests, by signing this document, that:
- The test data was not used during model training, validation, or hyperparameter tuning.
- The model was not exposed to the test data during development.
- The test data is fixed at the SHA hash recorded above and will not be modified before execution.

If any of these conditions cannot be attested, the test must be re-scoped to use auditor-curated data instead. Customer-asserted held-out integrity is the customer's representation; the auditor does not independently verify it but does record this representation in the result document.

### 3.3 Subgroup analysis (optional)

[CUSTOMER FILLS: If subgroup-stratified calibration analysis is in scope, list the subgroups here, e.g., by demographic attribute, by data source, by time period. Each subgroup must have ≥ 100 examples to support a Wilson interval calculation. If subgroups are not pre-specified here, no subgroup analysis is performed.]

---

## 4. Inference Pipeline

### 4.1 Pipeline specification

The model is queried for prediction on each test data example via the inference code at [AUDITOR FILLS: path to script in commit]. The inference code is frozen at git commit [AUDITOR FILLS: hash to be filled at lock time] and is not modified between this commit and the recording of all predictions.

### 4.2 Output processing

| Field | Value |
|---|---|
| How predictions are extracted | [CUSTOMER FILLS: e.g., softmax of final layer, then take class POSITIVE probability] |
| Any thresholding or transformation | [CUSTOMER FILLS: e.g., none / sigmoid scaling / temperature 1.0] |
| Numerical precision | [CUSTOMER FILLS: float32 / float64] |

### 4.3 Inference environment

| Field | Value |
|---|---|
| Hardware | [AUDITOR FILLS: CPU/GPU specification at execution time] |
| Library versions | [AUDITOR FILLS: frozen in requirements.txt at lock commit] |
| Random seed (if any) | [AUDITOR FILLS] |

The inference environment is recorded for reproducibility but is not the subject of the calibration claim.

---

## 5. Calibration Metrics

The following metrics are computed identically for the full test set and (if applicable) for each pre-registered subgroup.

### 5.1 Reliability bins

Predictions are partitioned into K = [CUSTOMER FILLS: typically 10] equal-width bins on the predicted probability axis. For each bin:

- Number of examples (n)
- Mean predicted probability
- Observed frequency of the positive class
- Wilson 95% confidence interval on the observed frequency

Bins with n < 30 examples are reported but excluded from the bin-pass-count statistic per Section 6.1 (insufficient sample for the Wilson interval).

### 5.2 Aggregate metrics

- **Brier score:** mean squared error between predicted probabilities and observed binary outcomes.
- **Brier skill score (BSS) against base-rate climatology:** 1 − (Brier_model / Brier_climatology), where Brier_climatology is the Brier score of always predicting the base rate.
- **Expected Calibration Error (ECE):** average across bins of |bin mean prediction − bin observed frequency|, weighted by bin example count. *Reported but not used in the primary decision criteria* — ECE is sample-size-sensitive and not interval-based.
- **Maximum Calibration Error (MCE):** maximum across bins of the same quantity.

---

## 6. Pre-Registered Decision Criteria

### 6.1 Primary decision

The model's calibration is classified into one of four pre-registered outcomes:

| Outcome | Criterion |
|---|---|
| **Calibrated (strong)** | At least [CUSTOMER FILLS: typically 9] of [K] bins have observed frequency within the Wilson 95% CI of the bin mean predicted probability, AND BSS > 0. |
| **Calibrated (acceptable)** | At least [CUSTOMER FILLS: typically 7] of [K] bins meet the Wilson criterion, AND BSS > 0. |
| **Calibration drift detected** | Fewer than 7 of K bins meet the Wilson criterion, OR BSS ≤ 0. |
| **Not calibrated** | Fewer than 5 of K bins meet the Wilson criterion. |

Bins with n < 30 are excluded from the count (denominator becomes K minus excluded bins).

### 6.2 Subgroup decisions (if applicable)

If subgroup analysis is in scope (Section 3.3), each subgroup is classified independently using the criteria above. The overall outcome is the worst of the per-subgroup outcomes.

---

## 7. Sanity Checks (auxiliary, not part of the primary outcome)

The following are reported alongside the primary decision but do not modify it:

### 7.1 Class balance

Reported actual base rate vs. customer-asserted base rate. Discrepancies > 5pp are flagged.

### 7.2 Prediction distribution

Histogram of predicted probabilities over the test set, with mean, median, and percentiles. Highly skewed distributions (e.g., > 90% of predictions in a single bin) reduce the statistical power of the calibration test and are noted.

### 7.3 Refusal / abstention behavior

If the model can abstain, refuse, or output a NULL prediction, the rate is reported. Abstained examples are excluded from calibration computation.

---

## 8. What This Test Does Not Claim

Registering this test makes none of the following claims:

- That the model is accurate, useful, or fit for any specific purpose.
- That the model is calibrated on data drawn from a different distribution than the test set.
- That the model is robust to adversarial inputs, distribution shift, or temporal drift.
- That the model is fair or unbiased across populations not enumerated in Section 3.3.
- That a "calibrated" outcome on this test implies regulatory approval, audit clearance, or compliance with any specific regulatory framework. Customers and downstream parties make those determinations independently.

A "calibrated" outcome means and only means: under the test data and decision criteria locked above, the model's predicted probabilities matched observed frequencies within the registered tolerances.

---

## 9. Test Logistics

### 9.1 Pre-test artifacts (committed before any prediction is computed)

The following are committed to git before execution:

- This pre-registration document (signed by both parties).
- The inference and analysis code at the frozen commit hash.
- The test data file (or its SHA-256 hash, if confidentiality requires the data itself remain private).
- The customer's signed attestation of held-out integrity (Section 3.2).

### 9.2 Test execution

The auditor runs the frozen analysis script once. All predictions are computed, all calibration metrics are calculated, and all results are written to a fixed output file before any inspection. Re-running the test is permitted only to verify reproducibility, not to revise outcomes.

### 9.3 Result reporting

The locked result document is drafted by the auditor and shared with the customer. The customer reviews the document for confidentiality redactions only — not for content. The customer may request that specific examples or non-aggregate data be redacted from the public version of the result document; the customer may not request that the outcome classification, primary metrics, or methodology summary be revised.

### 9.4 Disclosure of failure

If the test produces a "calibration drift detected" or "not calibrated" outcome, the result document records this outcome and is delivered to the customer. The customer is not contractually obligated to publish the result, but the result is not modified.

---

## 10. Lock and Provenance

This document is committed to git alongside the analysis code. The git commit hash for both is recorded in the result document.

The methodology, parameters (K, decision thresholds, subgroup definitions, inference pipeline), and analysis code are fully bound at the lock commit. No parameter, threshold, or definition above may be modified before the test outcome is reported.

| Item | Reference |
|---|---|
| Pre-registration commit hash | [AUDITOR FILLS at lock time] |
| Inference code commit hash | [AUDITOR FILLS at lock time] |
| Test data SHA-256 | [AUDITOR FILLS at lock time] |
| Customer signature | [CUSTOMER COUNTERSIGNS] |
| Auditor signature | [AUDITOR SIGNS] |

---

## 11. Pre-Test Status (as of lock date)

Recorded for context (not part of the test):

- [CUSTOMER FILLS: Any prior calibration analysis the customer has performed on this model, including any reported outcomes, methods used, and dates.]
- [CUSTOMER FILLS: Any production deployment status of the model — pre-launch, pilot, full production, etc.]
- [CUSTOMER FILLS: Any external claims the customer has made about this model's calibration (in marketing, regulatory filings, contracts, etc.) that this test is intended to verify or document.]

---

*End of Pre-Registration Template.*