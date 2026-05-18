# Result — ChatGPT-detector-roberta calibration audit v1

**Identifier:** `chatgpt-detector-roberta-calibration-v1`
**Status:** Locked. Not subject to revision.
**Date:** 2026-05-18.
**Author:** Earl Dixon.

**Pre-registration commit:** `71efcef` (lock commit covering pre-registration, analysis code, materialized corpus, model revision, RAID revision, resolved `ai_class_index`, and SHA-256 hashes).
**Output artifacts commit:** `4ecdd98` (lock commit covering `predictions.csv`, `calibration_scores.csv`, `calibration_summary.json`).
**Result commit:** This document, locked at TBD.

**Methodology pattern:** This audit followed the pre-registered methodology pattern documented in `docs/standards/AEPF_v0.1_WORKING_DRAFT.md` (lock commit `65c8035`).

---

## 1. Headline outcome

**This is an out-of-training-distribution calibration audit of `Hello-SimpleAI/chatgpt-detector-roberta`, evaluated on the RAID corpus (assembled after the detector's training, containing AI-generated text from 11 model families the detector was not trained on).**

**Outcome: NOT CALIBRATED.**

The detector achieves **67.8% accuracy at the 0.5 threshold** — which sounds reasonable in isolation — but its probability outputs produce **Brier skill score BSS = −0.16** against a 0.5-base-rate climatology, meaning the detector's confidence values are *worse* than a fixed 50/50 prediction as probabilistic forecasters. Zero of the six bins meeting the n ≥ 30 inclusion threshold pass the pre-registered Wilson 95% confidence-interval criterion. The detector has some discrimination signal but no probabilistic skill on this corpus.

**Bimodal output with bidirectional miscalibration.** The detector concentrates 86% of predictions at the two probability extremes — 56% in bin 0 (probability < 0.1) and 30% in bin 9 (probability ≥ 0.9). At the "human" end, it predicts mean probability 1.2% AI when the observed AI frequency is 34.3% — dramatically underconfident. At the "AI" end, it predicts mean probability 98.4% AI when the observed AI frequency is 77.9% — substantially overconfident. The four middle-low populated bins (1, 2, 3, 8) all fail in the same directions as the extremes.

**Concrete real-world reading.** Of the 596 essays the detector flagged with ≥90% confidence as AI-generated, **roughly 132 (22%) are actually human-written**. Of the 1,115 essays the detector classified with <10% confidence as essentially-certainly-human, **roughly 382 (34%) are actually AI-generated**. The detector's confidence values do not mean what they appear to mean; both directions are wrong, both magnitudes are large.

**The accuracy/BSS divergence is the methodological teaching point this audit demonstrates.** A user looking at 67.8% accuracy would conclude the detector somewhat works. The BSS of −0.16 says the probabilities it outputs to drive thresholded decisions are systematically wrong by 18 to 33 percentage points in the bins that matter. This is the gap an accuracy benchmark cannot expose and that a calibration audit is designed to surface.

---

## 2. Audit boundary

Reproduced verbatim from pre-registration §6 for prominent placement in the result document:

This audit tests, and only tests, the calibration of `Hello-SimpleAI/chatgpt-detector-roberta`'s predicted AI-generated probabilities against the RAID subsample defined in the pre-registration §3, under the analysis specified in pre-registration §4, against the decision criteria in pre-registration §5.

The audit does NOT test:

- Whether the detector is appropriate for use in any specific downstream application (classroom integrity, plagiarism detection, editorial review, employment screening, etc.).
- Whether the detector's accuracy is acceptable for any specific decision threshold. The audit reports accuracy at threshold 0.5 as an auxiliary metric, not a primary outcome.
- Whether the detector exhibits demographic bias. Liang et al. 2023 (Stanford) documented bias against non-native English writers in GPT detectors; that finding is real and important, but is a different question from calibration and is not tested here.
- Whether RAID is a representative test corpus for any specific real-world deployment context. RAID is the test data; conclusions are bound to RAID's distribution.
- Whether other AI-content detectors would produce similar results on the same corpus. This audit covers one specific model.

---

## 3. Interpretive constraints on the verdict

Reproduced from pre-registration §7. The NOT CALIBRATED verdict reached by this audit establishes:

- That on the RAID subsample specified in pre-registration §3, the detector's predicted probabilities deviate systematically from observed AI-generated frequencies under the registered analysis. Six included bins were measured; all six failed the Wilson criterion. BSS against the registered climatology is negative.

The NOT CALIBRATED verdict does NOT establish:

- That the detector is useless. The detector achieves 67.8% accuracy at threshold 0.5 on this corpus; it has *some* signal, just not calibrated probability magnitudes. A user thresholding the detector's outputs at decision boundaries calibrated empirically on a representative deployment corpus (rather than on the detector's nominal probabilities) might achieve better practical results than the calibration verdict alone suggests.
- That a recalibrated version of the same detector (e.g., temperature-scaled, Platt-scaled, isotonic-regression-corrected) would also be miscalibrated. Recalibration is a known remedy for miscalibrated classifiers, and a future audit could test a recalibrated variant. This audit measures the detector as-shipped.
- That AI-content detection as a category is unreliable. This is one model, one corpus. Other detectors may be calibrated where this one is not.

---

## 4. Aggregate metrics

| Metric | Value | Note |
|---|---|---|
| Total examples | 2,000 | 1,000 human + 1,000 AI-generated, balanced by construction |
| Base rate (in corpus) | 0.5000 | By construction of the balanced subsample |
| Accuracy at threshold 0.5 | 0.6780 | Auxiliary; not the primary outcome metric |
| Brier score (detector) | 0.2907 | |
| Brier score (climatology) | 0.2500 | Against fixed 0.5 prediction |
| **Brier skill score (BSS)** | **−0.1628** | **Negative; worse than fixed-0.5 prediction** |
| Expected calibration error (ECE) | 0.2791 | Weighted average of \|mean_pred − observed_freq\| across all populated bins |
| Maximum calibration error (MCE) | 0.3307 | Maximum \|mean_pred − observed_freq\| across included bins |
| Truncated fraction | 0.116 | 231 of 2,000 texts exceeded 512 tokens; first 512 used |

**Base-rate disclosure (pre-reg §3.2).** The BSS value of −0.16 is measured against a 0.5-base-rate climatology, which is the base rate of the balanced test corpus by construction. In real-world deployment contexts, the actual prevalence of AI-generated text is typically much lower than 50% (often 5–15%). Under a deployment-realistic prior, the climatology baseline (always predicting the lower base rate) becomes harder to beat, and the detector's BSS would typically be *worse* than the −0.16 reported here, not better. The headline BSS reflects calibration on the balanced corpus, not what BSS would be in a 10% prevalence context.

---

## 5. Per-bin reliability table

10 equal-width bins on the unit interval. First nine bins half-open at upper edge; tenth bin closed at both ends (pre-reg §4.2). Bins with n < 30 are excluded from the calibration verdict (pre-reg §4.2). Wilson 95% CI of observed positive-class frequency; the bin's mean predicted probability is tested against that interval.

| Bin | Range | n | Mean pred | Observed | Wilson lo | Wilson hi | Pass? |
|---|---|---|---|---|---|---|---|
| 0 | [0.00, 0.10) | 1,115 | 0.012 | 0.343 | 0.315 | 0.371 | **FAIL** |
| 1 | [0.10, 0.20) | 96 | 0.145 | 0.417 | 0.323 | 0.517 | **FAIL** |
| 2 | [0.20, 0.30) | 74 | 0.255 | 0.568 | 0.454 | 0.674 | **FAIL** |
| 3 | [0.30, 0.40) | 59 | 0.330 | 0.508 | 0.384 | 0.632 | **FAIL** |
| 4 | [0.40, 0.50) | 4 | 0.434 | 0.500 | — | — | excluded (n < 30) |
| 5 | [0.50, 0.60) | 5 | 0.543 | 0.800 | — | — | excluded (n < 30) |
| 6 | [0.60, 0.70) | 3 | 0.653 | 0.333 | — | — | excluded (n < 30) |
| 7 | [0.70, 0.80) | 17 | 0.748 | 0.706 | — | — | excluded (n < 30) |
| 8 | [0.80, 0.90) | 31 | 0.868 | 0.742 | 0.568 | 0.863 | **FAIL** |
| 9 | [0.90, 1.00] | 596 | 0.984 | 0.779 | 0.743 | 0.810 | **FAIL** |

**Bin coverage:** 6 of 10 bins included (n ≥ 30). **Bin passes:** 0 of 6.

---

## 6. Diagnostic findings (deeper analysis of headline patterns)

The bimodal output, the bidirectional miscalibration, and the real-world reading of those patterns are summarized in §1 (Headline outcome). This section provides the deeper per-bin analysis behind those summary statements.

### 6.1 Per-bin miscalibration direction and magnitude

All six bins meeting the n ≥ 30 inclusion threshold fail the Wilson criterion. The direction and magnitude of failure varies systematically:

**At the "human" end (bin 0, n = 1,115):** predicted mean 1.2%, observed 34.3%, Wilson CI [31.5%, 37.1%]. The detector's prediction sits 33.0 percentage points below the lower bound of the Wilson interval. Underconfident.

**Middle-low bins (1, 2, 3) (n = 96, 74, 59):** all underconfident, in the same direction as bin 0. Predicted probabilities 0.14, 0.26, 0.33 correspond to observed frequencies 0.42, 0.57, 0.51 respectively.

**Bin 8 (n = 31):** predicted mean 0.87, observed 0.74. Overconfident, in the same direction as bin 9.

**At the "AI" end (bin 9, n = 596):** predicted mean 98.4%, observed 77.9%, Wilson CI [74.3%, 81.0%]. The detector's prediction sits 17.4 percentage points above the upper bound. Overconfident.

The miscalibration is not localized to one end of the probability range; it is systematic across the entire populated range, with a directional flip occurring somewhere in the sparsely-populated middle bins. The four middle bins (4–7) have only 29 examples combined and were excluded for n < 30 — the detector rarely expresses calibrated uncertainty in the 0.4–0.8 range.

### 6.2 What the accuracy/BSS divergence demonstrates

The detector's 67.8% accuracy at the 0.5 threshold reflects its discrimination ability: when AI text has clear features the detector recognizes and human text lacks them, the detector ranks examples in roughly the right order. By that measure alone, the detector outperforms chance by 17.8 percentage points.

But the probabilities it outputs are systematically wrong by 18 to 33 percentage points. A user thresholding the detector's outputs on a deployment-realistic decision boundary — say, "flag if confidence ≥ 0.95" — will encounter false positive rates substantially higher than the confidence value suggests. The audit measures this gap directly. An accuracy benchmark, by reporting only the proportion of correct argmax predictions, hides it.

This is the kind of finding that calibration audits exist to produce, and that no amount of accuracy testing would have surfaced.

---

## 7. Exploratory post-hoc analysis — not part of the locked outcome

**The locked verdict (NOT CALIBRATED, BSS = −0.16, 0 of 6 bins passing) is final and determined entirely by the pre-registered methodology applied to the full 2,000-example corpus.** The analysis below was not specified in the pre-registration. It is presented here for diagnostic interest only — to inform interpretation of the locked verdict, not to modify it. The pre-registered decision criteria in §5 are not re-applied to the subsamples examined below.

### 7.1 Truncated-vs-non-truncated calibration subsamples

Of the 2,000 test corpus examples, 231 (11.6%) exceeded the detector's 512-token context window and were truncated to the first 512 tokens at inference time per pre-reg §4.1. To assess whether truncation contributes to the headline calibration failure, the corpus is post-hoc split into truncated (n = 231) and non-truncated (n = 1,769) subsamples and the aggregate metrics are computed separately on each.

| Metric | Truncated (n = 231) | Non-truncated (n = 1,769) | Full corpus (n = 2,000) |
|---|---|---|---|
| Accuracy at 0.5 | 0.8485 | 0.6557 | 0.6780 |
| Brier score | 0.1440 | 0.3099 | 0.2907 |
| BSS vs 0.5 climatology | **+0.4240** | **−0.2394** | **−0.1628** |

**The direction of this split is informative — and it rules out truncation as the driver of the headline finding.**

The truncated subsample (n = 231) shows substantially *better* calibration than the non-truncated subsample. Its BSS of **+0.42** is positive, meaning the detector's predictions on truncated texts are better as probabilistic forecasters than a fixed 0.5-prediction would be. The non-truncated subsample (n = 1,769) — where the detector saw the full text without truncation — shows BSS of **−0.24**, substantively worse than the corpus-wide BSS of −0.16.

Two implications:

**Truncation is not the cause of the headline calibration failure.** If truncation had degraded calibration, the truncated subsample would show worse BSS than the non-truncated. The opposite is observed. The 88.5% of the corpus where the detector operated on full text is the portion driving the negative BSS; the truncated 11.6% performs comparatively well.

**The headline verdict is robust.** Removing the 231 truncated examples and analyzing only the 1,769 non-truncated examples yields BSS −0.24 — a *stronger* failure than the headline. A reader who anticipated a "the truncation made the test unfair" rebuttal can see, from this split alone, that the rebuttal does not apply: the failure is on the texts the detector saw in full.

The most plausible explanation for the direction is a selection effect: long texts (those exceeding 512 tokens) tend to come from domains where stylistic AI signatures are more pronounced (books, abstracts, recipes), making detection structurally easier even when only the first 512 tokens are seen. Texts from shorter-form domains (reviews, Reddit, short news) populate the non-truncated subsample more heavily, and these may carry weaker AI-detection signals overall. This is descriptive, not causal — the exploratory split shows the direction without isolating the mechanism. The locked verdict applies regardless.

---

## 8. Methodology limitations

The following limitations apply to the headline finding and should be considered when interpreting the result:

**Balanced-corpus base rate.** The BSS of −0.16 is computed against a 0.5 climatology, the base rate of the balanced corpus by construction. Deployment contexts typically have AI prevalence in the 5–15% range, where the climatology baseline becomes harder to beat. The BSS in a deployment-realistic context would typically be worse than reported here, not better. This does not change the per-bin calibration findings, which are independent of the base rate.

**Truncation.** 11.6% of texts hit the 512-token boundary. The detector's outputs on these texts reflect only the first 512 tokens. Exploratory subsample analysis (§7.1) examines whether truncation effects are a material driver of the headline finding; the locked verdict applies to the full 2,000-example corpus regardless.

**Held-out integrity assumption.** The audit treats RAID as out-of-training-distribution for `Hello-SimpleAI/chatgpt-detector-roberta` based on the detector's published training procedure (trained on HC3, a distinct corpus). The audit operator did not independently verify the detector's exact training data contents. RAID's curation post-dates the detector's training and includes AI model families the detector cannot have seen, which supports the OOD characterization, but the strict assertion is bounded by what the operator can verify.

**Decoder-agnostic AI labeling.** RAID labels are taken as ground truth without independent verification. The audit binds to RAID's labels as authoritative; any errors in RAID's labeling propagate into the audit's findings.

**Single-detector scope.** This audit covers one specific model at one specific revision. Generalization to other AI-content detectors requires separate audits.

**No fairness or bias measurement.** Liang et al. 2023 documented bias against non-native English writers in GPT detectors. This audit does not measure that bias; it measures calibration on the RAID corpus. A detector can be miscalibrated without being unfair, and unfair without being miscalibrated; the two questions are distinct.

---

## 9. Provenance

**Pre-registration commit:** `71efcef` (lock commit covering pre-registration document, analysis code, materialized corpus, model revision, RAID revision, resolved `ai_class_index`, and SHA-256 hashes).

**Output artifacts commit:** `4ecdd98` (lock commit covering `predictions.csv`, `calibration_scores.csv`, `calibration_summary.json`).

**Pinned model revision:** `d2b342c61775d5dd0221808a79983ed3b86ffd86`

**Pinned RAID dataset revision:** `865cac74188466cb0c3b7574a10204007b57a459`

**Resolved `ai_class_index`:** `1` (from `id2label = {0: 'Human', 1: 'ChatGPT'}` at the pinned model revision).

**Test data SHA-256:** `a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47`

**Test corpus composition:**
- 1,000 human-written texts, equal proportions across 8 domains (abstracts, books, news, poetry, recipes, reddit, reviews, wiki).
- 1,000 AI-generated texts, stratified across 11 model families as defined by RAID's `model` metadata column: `chatgpt` (89), `cohere` (89), `cohere-chat` (90), `gpt2` (93), `gpt3` (90), `gpt4` (88), `llama-chat` (92), `mistral` (93), `mistral-chat` (93), `mpt` (92), `mpt-chat` (91). Domain breakdown approximately equal across the same 8 domains.
- 11.6% (231/2000) of texts exceeded 512 tokens and were truncated at inference per pre-reg §4.1.

**Inference environment:**
- Operating system: Windows 11
- Python: 3.11
- transformers: 5.8.0
- torch: 2.10.0
- datasets: 4.8.5
- huggingface_hub: 1.13.0
- numpy: 2.4.3
- pandas: 3.0.2
- `KMP_DUPLICATE_LIB_OK=TRUE` set to permit coexistence of LLVM and Intel OpenMP runtimes. This environment variable does not affect numerical results for the single-pass forward inference used in this audit.

**Inference runtime:** approximately 3 minutes for 2,000 examples on CPU.

**Audit commissioner:** No external commercial customer commissioned this audit. It was conducted as a public demonstration of the methodology, structurally analogous to the DistilBERT-SST2 and Toxic-BERT case studies in this repository. The audit operator (Earl Dixon) bears responsibility for methodology decisions; the locked artifacts are reproducible by any reader from the cited commits.

**Methodology pattern:** This audit followed the pre-registered methodology pattern documented in `docs/standards/AEPF_v0.1_WORKING_DRAFT.md` (lock commit `65c8035`).

---

## 10. Reproducibility note for §7.1

The truncated-vs-non-truncated subsample metrics in §7.1 are computed directly from the locked `predictions.csv`. Any reader can verify the numbers by re-running the following snippet from the case study folder:

```
python -c "
import numpy as np
import pandas as pd
p = pd.read_csv('predictions.csv')
for tag, sub in (('truncated', p[p['truncated']==1]), ('non_truncated', p[p['truncated']==0])):
    y = sub['is_ai_generated'].values
    probs = sub['predicted_prob_ai'].values
    acc = float(np.mean((probs >= 0.5) == y))
    brier = float(np.mean((probs - y) ** 2))
    brier_clim = float(np.mean((0.5 - y) ** 2))
    bss = float(1.0 - brier / brier_clim)
    print(f'{tag}: n={len(sub)} acc={acc:.4f} brier={brier:.4f} bss={bss:+.4f}')
"
```

Expected output reproduces the §7.1 table values exactly within float-precision tolerance.

---

*End of result document. Locked irrespective of outcome favorability. The verdict NOT CALIBRATED is recorded under the pre-registered methodology and decision criteria. Subject to no revision.*