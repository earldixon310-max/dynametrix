# Pre-registration — ChatGPT-detector-roberta calibration audit v1

**Status:** Draft pending lock commit.
**Identifier:** `chatgpt-detector-roberta-calibration-v1`
**Date:** 2026-05-17.
**Author:** Earl Dixon.

---

## 1. The claim being tested

The HuggingFace model `Hello-SimpleAI/chatgpt-detector-roberta` produces probabilistic predictions of whether a piece of text is AI-generated. Its outputs are used downstream in real-world contexts (educational integrity systems, editorial workflows, plagiarism detection software) where the numerical confidence value drives decisions about specific individuals.

This pre-registration tests one narrow but consequential claim: that the detector's predicted probabilities are calibrated when applied to the RAID benchmark corpus (Robust AI Detection, Dugan et al. 2024), a public test set assembled after the detector was trained and containing outputs from AI model families the detector was not trained on.

Specifically: across 10 reliability bins of predicted probability on the RAID subsample defined in Section 3, the detector's predicted probabilities will fall within Wilson 95% confidence intervals of observed AI-generated frequencies for at least 8 of the bins meeting the n ≥ 30 sample-size requirement, alongside a positive Brier skill score against base-rate climatology.

This is an audit of calibration on an out-of-training-distribution corpus, not a test of the detector's in-distribution calibration on the data it was trained on.

---

## 2. System under evaluation

### 2.1 Model

**Name:** `Hello-SimpleAI/chatgpt-detector-roberta`
**Source:** HuggingFace Hub
**Revision (HF commit hash):** [TO BE FILLED AT LOCK]
**Architecture:** RoBERTa-based binary classifier
**Output:** Two-class softmax over (human-written, AI-generated). The audit consumes the probability of the AI-generated class.

The model was published by SimpleAI in 2023 and trained primarily on the HC3 corpus (Human-ChatGPT Comparison Corpus), which consists of human-written and ChatGPT-3.5-era responses to the same prompts. The detector has approximately 1 million reported HuggingFace downloads and appears in real-world detection pipelines.

### 2.2 What this audit does NOT modify

The audit downloads the model at the pinned revision and runs inference. No fine-tuning, no temperature calibration, no threshold adjustment, no preprocessing of inputs beyond what the model's tokenizer applies. The detector is evaluated as-shipped.

---

## 3. Test data

### 3.1 Source corpus

The audit uses a subset of the **non-adversarial split of the RAID benchmark** (Robust AI Detection), a public dataset for AI-text detection released by Liam Dugan and colleagues in 2024. RAID contains:

- Human-written text drawn from multiple public sources across domains (news, books, abstracts, recipes, reviews, Reddit, Wikipedia, etc.).
- AI-generated text from multiple model families (GPT-4, Claude-3, Llama-3, Mistral, Cohere, and others), generated on prompts matched to the human-text domains.
- Multiple decoding strategies for the AI generations (greedy, sampling, etc.).
- An adversarial split containing texts modified to evade detection (paraphrasing, character substitution, etc.).

**This audit registers only the non-adversarial split.** RAID's adversarial split tests resistance to evasion, which is a different claim from calibration on natural text and should be evaluated under a separate pre-registration if and when it is tested. Including the adversarial split here would conflate two distinct properties (calibration vs evasion resistance) and would invite the rebuttal "the test was unfair because adversarial inputs are out-of-deployment." Registering the non-adversarial split forecloses that defense.

RAID was published after `Hello-SimpleAI/chatgpt-detector-roberta` was trained, so the AI-generated texts in RAID are from model families the detector did not see in training. The corpus is publicly available at the official RAID repository on HuggingFace Hub.

**Dataset revision pinning.** RAID lives on HuggingFace Hub and may be updated, errata-corrected, or have rows added or removed over time. To prevent silent drift between the locked corpus and what a future re-run would materialize, the RAID dataset's revision hash (HuggingFace Hub commit) is queried and recorded at setup time, locked into this pre-registration in Section 9, and verified by the analysis script at every subsequent run. Any mismatch causes the script to refuse to proceed. This parallels the model-revision pinning in Section 2.1.

### 3.2 Subsample selection

A balanced subsample of 2,000 examples is drawn from RAID's non-adversarial split under the following pre-registered procedure:

- **Total size:** 2,000 examples (1,000 human-written, 1,000 AI-generated).
- **Domain stratification:** The 1,000 examples on each side (human and AI) are drawn in equal proportions across the domains present in RAID's non-adversarial split (news, books, abstracts, recipes, reviews, Reddit, Wikipedia, and any other domains present). If a domain provides fewer examples than its allocated proportion requires, the remainder is redistributed proportionally across the other domains. The exact domain breakdown is locked in the materialization step and recorded in the result document.
- **AI model-family stratification:** The 1,000 AI-generated examples are drawn in equal proportions across the model families **as defined by RAID's own metadata column** (the `model` or equivalent field in the RAID schema at the pinned dataset revision). RAID's authors made the grouping choices when building the benchmark; this audit binds to those choices rather than introducing its own grouping (which would require judgment calls about whether GPT-3.5 and GPT-4 are one family, whether Llama-2-7b and Llama-2-70b are one family, etc.). The exact list of RAID-defined families and the per-family count is locked at materialization and recorded in the result document. This stratification prevents the audit from accidentally becoming a calibration test for one dominant model family rather than for AI-generated text broadly.
- **Decoding-strategy handling:** Within each (domain × model family) cell, when RAID provides multiple decoding strategies (e.g., greedy, sampling) for the same prompt, one is selected uniformly at random. The selection is reproducible from the random seed.
- **Random seed:** 150914 (the same seed used for the toxic-bert audit, for documentation cleanliness).
- **Length filter:** Examples with fewer than 100 characters are excluded (too short for the detector to extract useful signal). There is no upper bound on character length; texts that exceed the detector's tokenized context window are truncated at inference time per Section 4.1.

**Base-rate disclosure.** The 50/50 sampling produces a corpus base rate of 0.5 by construction. The Brier skill score computed in Section 4.2 is therefore measured against a 0.5-base-rate climatology baseline. This is not the base rate of any specific real-world deployment context — in classroom essay screening or editorial review pipelines, the actual prevalence of AI-generated text is typically much lower than 50%. The reported BSS reflects calibration on the balanced corpus, not what BSS would be under a deployment-realistic prior. The result document MUST disclose this distinction explicitly so the BSS number is not read out of context.

The subsample is materialized as a single CSV file (`chatgpt_detector_roberta_test_set.csv`) at setup time, with columns: `id`, `text`, `is_ai_generated` (0 or 1), `source_domain`, `source_model` (empty for human-written). The CSV is hashed (SHA-256) and the hash is committed to this pre-registration at the lock commit.

### 3.3 Held-out integrity

The detector model `Hello-SimpleAI/chatgpt-detector-roberta` was trained primarily on HC3, which is distinct from RAID. To the audit operator's knowledge, RAID examples were not used in the detector's training. This pre-registration treats RAID as out-of-training-distribution test data on the basis of the detector's published training procedure, while acknowledging that the operator cannot independently verify the exact training corpus contents.

The detector's outputs on the RAID subsample have not been examined prior to the lock commit. The operator has not run inference on any RAID example with this detector before lock.

---

## 4. Methodology

### 4.1 Inference

For each example in the subsample:

- Tokenize the text using the detector's published tokenizer at the pinned revision.
- **Truncation strategy:** texts whose tokenized length exceeds the detector's 512-token context window are truncated to the first 512 tokens. No sliding-window aggregation, no chunking, no mean-or-max pooling across multiple chunks. The detector is applied exactly once per example, to the first 512 tokens. This matches the most common real-world usage pattern (deployed pipelines typically feed text into a detector as a single forward pass) and is the simplest reproducible choice. The result document records the fraction of examples that were truncated.
- Run the model forward pass. Obtain the 2-element logit vector.
- **Probability extraction convention.** The predicted probability that the text is AI-generated is computed as `softmax(logits)[ai_class_index]`, where `ai_class_index` is determined by inspecting the model's `id2label` mapping (from the model's `config.json` at the pinned revision) and selecting the index whose label corresponds to AI-generated text. The script MUST verify the `id2label` mapping at load time and refuse to proceed if the AI-generated class is not unambiguously identifiable (e.g., if the labels are non-standard or ambiguous). The script MUST NOT hard-code the class index. The result document records the resolved `ai_class_index` and the full `id2label` dictionary for traceability.
- Record (example_id, true_label, predicted_probability, truncated_flag).

Inference is deterministic given the pinned model revision and fixed tokenization. No sampling, no temperature modification, no ensemble.

### 4.2 Calibration analysis

**Reliability binning.** All 2,000 predicted probabilities are pooled. Predictions are assigned to 10 equal-width bins on the unit interval. The first nine bins are half-open at the upper edge: [0.0, 0.1), [0.1, 0.2), …, [0.8, 0.9). The tenth bin is closed at both ends: [0.9, 1.0]. Predicted probabilities of exactly 1.0 therefore belong to the tenth bin; predicted probabilities of exactly 0.1, 0.2, …, 0.9 belong to the bin whose lower edge equals that value. Bins with fewer than 30 examples are excluded from the reliability evaluation and reported as excluded in the result document.

**Per-bin Wilson interval.** For each included bin, the Wilson 95% confidence interval is computed for the observed AI-generated frequency in that bin (proportion of bin examples with `is_ai_generated = 1`). A bin passes the calibration criterion if the bin's mean predicted probability falls within that Wilson interval.

**Brier skill score.** BSS is computed as 1 − (Brier_detector / Brier_climatology), where Brier_climatology is the Brier score of always predicting the corpus base rate (0.5 by construction of the balanced subsample).

**Auxiliary metrics:** accuracy (at threshold 0.5), ECE (expected calibration error across all bins, weighted by bin size), MCE (maximum calibration error across included bins).

---

## 5. Decision criteria

The detector's calibration on the RAID subsample is classified into one of four outcomes based on:

(a) **Bin pass count:** the number of included bins (n ≥ 30) that pass the Wilson criterion, expressed as a proportion of total included bins.

(b) **Skill:** whether BSS > 0 against the 0.5-base-rate climatology.

### 5.1 Bin coverage floor

Let **N** = number of bins among the 10 with n ≥ 30 examples. Let **K** = number of those N bins where the bin's mean predicted probability falls within the Wilson 95% CI of its observed AI-generated frequency.

- If **N < 5**, the outcome is **INSUFFICIENT BIN COVERAGE**. No calibration verdict is recorded. The result document records the bin-coverage distribution and explains why the test was underpowered.
- If **N ≥ 5**, proceed to Section 5.2.

### 5.2 Outcome classification (when N ≥ 5)

The pass-fraction thresholds are proportions of N. Thresholds use ceiling on the right-hand side of strict inequalities.

| Pass fraction (K/N) | Skill (BSS) | Outcome |
|---|---|---|
| K ≥ ⌈0.9 × N⌉ | BSS > 0 | **CALIBRATED (strong)** |
| K ≥ ⌈0.8 × N⌉ | BSS > 0 | **CALIBRATED (acceptable)** |
| ⌈0.6 × N⌉ ≤ K < ⌈0.8 × N⌉ | BSS > 0 | **CALIBRATION DRIFT DETECTED** |
| K < ⌈0.6 × N⌉, OR BSS ≤ 0 | (any) | **NOT CALIBRATED** |

Concrete thresholds for representative N:

| N | Strong | Acceptable | Drift | Not calibrated |
|---|---|---|---|---|
| 5 | K ≥ 5 | K ≥ 4 | K = 3 | K ≤ 2 |
| 6 | K ≥ 6 | K ≥ 5 | K = 4 | K ≤ 3 |
| 7 | K ≥ 7 | K ≥ 6 | K = 5 | K ≤ 4 |
| 8 | K ≥ 8 | K ≥ 7 | K = 5 | K ≤ 4 |
| 9 | K ≥ 9 | K ≥ 8 | K = 6 or 7 | K ≤ 5 |
| 10 | K ≥ 9 | K ≥ 8 | K = 6 or 7 | K ≤ 5 |

The outcome is recorded irrespective of which classification applies. The result document records the exact outcome under this classification, including all cases where the outcome is unfavorable to the detector.

---

## 6. Audit boundary

This audit tests, and only tests, the calibration of `Hello-SimpleAI/chatgpt-detector-roberta`'s predicted AI-generated probabilities against the RAID subsample defined in Section 3, under the analysis specified in Section 4, against the decision criteria in Section 5.

The audit does NOT test:

- Whether the detector is appropriate for use in any specific downstream application (classroom integrity, plagiarism detection, editorial review, employment screening, etc.). Calibration is one property among many that a deployment decision would consider; fairness, robustness to adversarial paraphrasing, cross-language behavior, and many other properties are out of scope.
- Whether the detector's accuracy is acceptable for any specific decision threshold. The audit reports accuracy at threshold 0.5 as an auxiliary metric, not a primary outcome.
- Whether the detector exhibits demographic bias. Liang et al. 2023 (Stanford) documented bias against non-native English writers in GPT detectors; that finding is real and important, but is a different question from calibration and is not tested here.
- Whether RAID is a representative test corpus for any specific real-world deployment context. RAID is the test data; conclusions are bound to RAID's distribution.
- Whether other AI-content detectors would produce similar results on the same corpus. This audit covers one specific model.

---

## 7. Interpretive constraints on the verdict

Regardless of which verdict is reached, the result document MUST observe the following interpretive constraints:

**A CALIBRATED (strong or acceptable) verdict establishes:**

- That on the RAID subsample specified in Section 3, the detector's predicted probabilities fall within Wilson 95% confidence intervals of observed AI-generated frequencies for the registered proportion of included bins, with positive Brier skill.

**A CALIBRATED verdict does NOT establish:**

- That the detector is calibrated on text distributions other than RAID.
- That the detector should be used to make consequential decisions about individuals. Calibration on a benchmark is necessary but not sufficient for deployment appropriateness.
- That the detector is fair or unbiased.
- That the detector's confidence values can be interpreted as probabilities in any context outside the registered test.

**A CALIBRATION DRIFT DETECTED or NOT CALIBRATED verdict establishes:**

- That on the RAID subsample specified in Section 3, the detector's predicted probabilities deviate systematically from observed AI-generated frequencies under the registered analysis.

**A CALIBRATION DRIFT DETECTED or NOT CALIBRATED verdict does NOT establish:**

- That the detector is useless. The detector may rank examples correctly (high ROC-AUC) while producing miscalibrated probability magnitudes. Calibration miscarriage is a specific finding, not a global condemnation.
- That a recalibrated version of the same detector (e.g., temperature-scaled, Platt-scaled, isotonic-regression-corrected) would also be miscalibrated. Recalibration is a known remedy for miscalibrated classifiers, and a future audit could test a recalibrated variant.
- That AI-content detection as a category is unreliable. This is one model, one corpus.

**Required disclosures.** The result document MUST disclose:

- The exact number of included bins (n ≥ 30) and the exact count of bins passing the Wilson criterion.
- The full reliability table, including excluded bins.
- The Brier score and Brier skill score, with the climatology baseline made explicit.
- The model revision hash and the test data SHA-256, so the audit is reproducible end-to-end.
- The audit operator and the fact that no commercial customer commissioned this audit (it is a public demonstration of the methodology, structurally analogous to the DistilBERT-SST2 and Toxic-BERT case studies in this repository).

---

## 8. Operational notes

**Pre-lock integrity.** The detector's outputs on RAID have not been examined prior to lock. The setup phase materializes the test data and computes its SHA-256 but does not run inference.

**Post-lock modifications.** The model revision, the test data, the analysis code, and the decision criteria MUST NOT be modified between the lock commit and the result document commit. Operational fixes (dependency updates, runtime environment configuration, OpenMP-conflict workarounds analogous to the DistilBERT case) that do not alter methodology are permitted but MUST be disclosed in the result document.

**Re-running for reproducibility.** The analysis is fully deterministic given the pinned model revision and the locked test data. Re-running the inference and analysis should produce numerically equivalent outputs within float-precision tolerance.

**Single execution.** The audit is run once after the lock commit. The result document records that single execution. Re-runs for reproducibility verification do not produce new outcome documents.

---

## 9. Provenance

**Author:** Earl Dixon.

**Lock commit:** TBD.

**Pinned model revision:** TBD (filled at setup; HuggingFace Hub commit hash for `Hello-SimpleAI/chatgpt-detector-roberta`).

**Pinned RAID dataset revision:** TBD (filled at setup; HuggingFace Hub commit hash for the RAID dataset at materialization time).

**Resolved `ai_class_index`:** TBD (filled at setup; from the model's `id2label` mapping at the pinned revision).

**Test data SHA-256:** TBD (filled at setup; SHA-256 of the materialized subsample CSV).

**Conformance:** This evaluation's evidence preservation conforms to the AEPF v0.1 Working Draft (`docs/standards/AEPF_v0.1_WORKING_DRAFT.md`, locked at commit `65c8035`).

**Companion artifacts (locked together at the lock commit):**

- This pre-registration document.
- `chatgpt_detector_roberta_calibration.py` (the analysis script).
- `chatgpt_detector_roberta_test_set.csv` (the materialized RAID subsample).
- `chatgpt_detector_roberta_test_set_sha256.txt` (the data hash).
- `model_revision.txt` (the pinned HuggingFace model revision).
- `requirements.txt` (Python dependency pinning).

---

*End of pre-registration. Status: Draft pending lock commit.*