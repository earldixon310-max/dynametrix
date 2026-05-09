# Toxic-BERT Calibration Verification v1 — Outcome

**Test identifier:** `toxic-bert-calibration-v1`
**Pre-registration:** `case_studies/toxic_bert/PRE_REGISTRATION_TOXIC_BERT_v1.md` (locked under git commit `1cca213` on 2026-05-06)
**Run date:** 2026-05-06
**Customer:** Earl Dixon (self-audit, public demonstration)
**Auditor:** Earl Dixon
**Status:** Locked outcome. Per pre-registration Section 11, this result document is bound and not subject to revision.

---

## Summary

The toxicity classification model `unitary/toxic-bert` (HuggingFace revision `4d6c22e7…`) was evaluated for calibration on a 5,000-example deterministic subsample of the Civil Comments validation split, drawn at seed `150914` under the pre-registered methodology.

**Outcome: Calibration drift detected.** Of the 10 reliability bins, all 10 contained sufficient examples (n ≥ 30) for inclusion; 5 of 10 passed the Wilson criterion. The pre-registered decision criteria classify this as the third-best of four outcome tiers — the model is doing meaningful predictive work but its probabilities do not reliably track observed frequencies under the registered protocol.

The result is more nuanced than the prior DistilBERT-SST-2 audit and reveals a different failure mode. The model achieves **94.5% accuracy** and a **+0.349 Brier skill score**, both substantially better than naive baselines. The Expected Calibration Error is **2.2%** — a small overall miscalibration. But the **Maximum Calibration Error is 18.4%**, concentrated in the middle-to-high probability range, where the model is systematically **overconfident**: when it predicts 60–70% toxicity, the actual rate is 47.7%; when it predicts 70–80%, the actual rate is 58.5%. Combined with a smaller but meaningful **underconfidence** in the lowest bin (predicted 0.87%, observed 2.21%), the model's probabilistic outputs misrepresent the underlying uncertainty in a structured rather than uniform way.

This is exactly the kind of finding the methodology was designed to surface, and the second public case study in which a recognizable HuggingFace-published model fails the calibration audit despite passing the accuracy claim its model card foregrounds.

---

## Outcome per Pre-Registered Decision Criteria

The following decision rules were locked in advance (pre-registration Section 6.1):

| Outcome | Criterion | Met? |
|---|---|---|
| Calibrated (strong) | ≥ ceil(0.9 × included_bins) bins pass + BSS > 0 | No (5 < 9) |
| Calibrated (acceptable) | ≥ ceil(0.8 × included_bins) bins pass + BSS > 0 | No (5 < 8) |
| **Calibration drift detected** | **Fewer than acceptable threshold but not fewer than drift floor; here, 5–7 of 10 bins pass, or BSS ≤ 0.** | **Yes (5 of 10 bins pass; BSS positive)** |
| Not calibrated | Fewer than ceil(0.5 × included_bins) bins pass | — |

With 10 bins included (no exclusions for n < 30 — the subsample populated every bin sufficiently), the proportional thresholds were `strong=9, acceptable=8, drift=5`. **Pass count: 5 of 10 included bins.** This sits exactly at the drift threshold and well below the acceptable threshold; combined with positive BSS, the outcome is **"Calibration drift detected."**

---

## Result Detail

### Sample summary

| Field | Value |
|---|---|
| Model | `unitary/toxic-bert` |
| Model revision (HF commit) | `4d6c22e74ba2fdd26bc4f7238f50766b045a0d94` |
| Test data | Civil Comments validation split (5,000-example deterministic subsample) |
| Subsample seed | `150914` |
| Subsample CSV SHA-256 | `647436da227d2231822a3d57fd60c7a153b63dfba97c290655b9f8838b71dc33` |
| Examples scored | 5,000 |
| Base rate (observed toxic) | 7.26% |

### Aggregate metrics

| Metric | Value | Interpretation |
|---|---|---|
| Accuracy (auxiliary) | **0.9446** | 94.46% top-class agreement at threshold 0.5 |
| Brier score | **0.0438** | Low absolute squared error |
| Brier climatology | 0.0673 | Brier of always predicting the base rate |
| **Brier skill score** | **+0.3489** | Strongly positive; predictions far better than base-rate |
| Expected Calibration Error | **0.0218** | 2.2 percentage points average gap |
| **Maximum Calibration Error** | **0.1842** | **18.4 percentage points worst-bin gap** |

### Per-bin reliability table

| Bin | Range | n | Mean predicted | Observed freq | Wilson 95% CI | Pass | Direction |
|---:|---|---:|---:|---:|---|:---:|:---:|
| 0 | [0.00, 0.10) | 4,347 | 0.0087 | 0.0221 | [0.0181, 0.0269] | **fail** | underconfident |
| 1 | [0.10, 0.20) | 178 | 0.1444 | 0.1910 | [0.1400, 0.2550] | PASS | — |
| 2 | [0.20, 0.30) | 96 | 0.2441 | 0.2812 | [0.2011, 0.3783] | PASS | — |
| 3 | [0.30, 0.40) | 65 | 0.3559 | 0.2923 | [0.1958, 0.4120] | PASS | — |
| 4 | [0.40, 0.50) | 58 | 0.4431 | 0.2759 | [0.1775, 0.4020] | **fail** | overconfident |
| 5 | [0.50, 0.60) | 54 | 0.5610 | 0.5370 | [0.4061, 0.6631] | PASS | — |
| 6 | [0.60, 0.70) | 44 | 0.6615 | 0.4773 | [0.3375, 0.6206] | **fail** | overconfident |
| 7 | [0.70, 0.80) | 41 | 0.7456 | 0.5854 | [0.4337, 0.7224] | **fail** | overconfident |
| 8 | [0.80, 0.90) | 45 | 0.8473 | 0.7556 | [0.6133, 0.8576] | PASS | — |
| 9 | [0.90, 1.00] | 72 | 0.9495 | 0.8750 | [0.7792, 0.9328] | **fail** | overconfident |

The five failing bins fail in two distinct patterns:

- **Bin 0 (largest by far, 4,347 examples / 86.9% of subsample):** model is *underconfident*. It predicts ~0.9% toxic; the actual rate is 2.2% — meaning content the model rates as "almost certainly safe" is actually toxic at 2.5× the predicted rate.
- **Bins 4, 6, 7, 9 (combined 215 examples / 4.3% of subsample):** model is *overconfident*. The middle-to-high confidence bands consistently predict probabilities above what the data supports, with the most severe miscalibration at bin 6 (predicted 66.2% vs. observed 47.7% — an 18.4-percentage-point gap).

---

## Diagnostic Reading

### The model is doing real predictive work

The Brier skill score of **+0.35** is substantially better than the DistilBERT result on its respective task and meaningfully above zero. Accuracy at threshold 0.5 is **94.5%**. The overall Brier score is **0.044** — low. By any single-number summary of model quality on this task, `unitary/toxic-bert` performs as advertised. This is not a "the model is broken" finding.

### But its probabilities are not interchangeable with reliable confidence

The structured failure pattern — overconfidence concentrated in the 40–80% predicted-probability range — is consequential because that range is exactly where **threshold-based decisions** live in production toxicity-detection pipelines. A content-moderation system that auto-flags content above 0.7 expects 70% of flagged items to actually be toxic, but on this audit's data, only **58.5%** would be. A system that auto-blocks content above 0.6 would expect 60%, but actually see **47.7%**. The implied positive-action rate at moderate-confidence thresholds is overstated by as much as roughly **18 percentage points** relative to observed toxicity.

### The bin-0 finding is the largest-volume issue

86.9% of the subsample sits in bin 0 (predicted toxicity < 10%). The model says ~0.9% toxic; reality is 2.2%. In production this means: a system that whitelists content with predicted toxicity < 1% (a reasonable auto-pass threshold) will let through actually-toxic content at **2.5× the rate the model's probabilities suggest**. The absolute miscalibration is small (0.87% vs. 2.21%, a 1.3-percentage-point gap), but the relative miscalibration is significant for high-throughput moderation pipelines where small per-item errors compound across millions of items.

### Comparison to DistilBERT v1

The two audits surface qualitatively different calibration failure modes:

| Aspect | DistilBERT-SST-2 v1 | Toxic-BERT v1 |
|---|---|---|
| Outcome tier | Not calibrated (worst) | Calibration drift detected (third) |
| Failed bins | 2 of 2 included | 5 of 10 included |
| Distribution shape | **Bimodal** — 95% of predictions at extremes | **Spread** — meaningful predictions across all bins |
| Failure direction | Symmetric overconfidence at both extremes | Underconfidence at low end + overconfidence in middle/upper |
| Accuracy | 91.06% | 94.46% |
| BSS | +0.667 | +0.349 |
| ECE | 7.20% | 2.18% |
| MCE | 8.73% | 18.42% |

The methodological point: **the same protocol, applied to two different model architectures on two different tasks, produces two structurally different calibration findings.** Neither is the "expected" pattern that a casual reading would predict. DistilBERT's bimodal extreme overconfidence and Toxic-BERT's spread-but-middle-overconfident behavior are both real and both diagnostic. A practice that audits enough models would build a catalog of recognizable failure modes; this is what the methodology generates.

### The pre-recorded prior expectation was partially right

Pre-registration Section 11 recorded a prior expectation that this audit would also produce a "Not calibrated" outcome with bimodal overconfidence similar to DistilBERT. **The expectation is partially refuted:** the outcome is "Calibration drift detected" rather than "Not calibrated", and the prediction distribution is not bimodal. **The expectation is partially confirmed:** overconfidence is present in the middle-to-upper bins. Recording the prior in advance and discussing its partial refutation here (rather than retroactively claiming the result was expected all along) is the methodological discipline at work.

---

## What This Test Does and Does Not Falsify

### Falsified

- The pre-registered calibration claim: that ≥ 8 of 10 bins pass the Wilson criterion AND BSS > 0. Falsified at 5 of 10 bins passing.
- The implicit assumption that this model's predicted probabilities, especially in the 40–80% range, are reliable as probabilities. Falsified under the registered protocol.

### Not falsified

- The model's accuracy on Civil Comments validation (94.46%, broadly consistent with the model card's claims).
- The model's Brier skill score (strongly positive at +0.349 — predictions are far better than the base rate).
- The model's fitness for argmax-based binary classification (toxic vs. non-toxic) at threshold 0.5.
- The model's calibration in bins 1, 2, 3, 5, and 8 specifically.
- The model's behavior on out-of-distribution toxicity data (HateCheck, ETHOS, Twitter, etc. — not in scope for v1).
- The model's fairness or calibration across demographic subgroups (Civil Comments has identity labels but subgroup analysis was explicitly out of scope per Section 3.3).
- That a recalibration layer (Platt scaling, isotonic regression, temperature scaling) could not improve calibration on this model. A v2 audit could test this.

---

## Implications for Users of the Audited Model

If you are using `unitary/toxic-bert` and your application:

- **Uses only the predicted class** (binarized at threshold 0.5) for moderation decisions: the audit does not contraindicate your usage. Accuracy is as advertised.
- **Uses a confidence threshold in the 40–80% range** to route content to human review or automated action: the audit warns that the threshold's actual operating point differs from its nominal value by 7 to 18 percentage points. A human-review threshold of 0.6 will route content at an actual ~48% toxicity rate, not 60%. Empirical re-calibration on your own validation data is recommended.
- **Whitelists content below a low predicted-toxicity threshold** (e.g., < 0.05 or < 0.10): the audit warns that the model is underconfident at the very low end. Content the model rates 0.87% will be actually toxic at 2.21% — about 2.5× the predicted rate. For high-throughput pipelines, this matters at scale.
- **Aggregates predictions across users or groups**: subgroup calibration was out of scope for v1. Civil Comments has identity labels and a v2 audit could test demographic-stratified calibration. Not addressed here.

A v2 audit could test whether common recalibration techniques (temperature scaling, Platt scaling, isotonic regression) restore calibration on this model under the same protocol, or whether subgroup calibration shifts the picture further. Both would be separately pre-registered.

---

## Implementation Observations

### Output extraction

The model produces 6 sigmoid outputs (`toxic`, `severe_toxic`, `obscene`, `threat`, `insult`, `identity_hate`). v1 audits only the `toxic` head (index 0). The other heads could each be their own pre-registration but were explicitly out of scope per Section 2.1. Per-bin analysis assumes the toxic head's sigmoid output is the calibration target; whether multi-label calibration interactions exist (e.g., `toxic` predictions correlated with `severe_toxic` confidence) is a v2 question.

### Subsample integrity

The 5,000-example subsample was deterministically drawn from the 97,320-example Civil Comments validation split using Python's `random.Random(150914).shuffle()` followed by selecting the first 5,000 sorted indices. The resulting CSV's SHA-256 hash (`647436da…`) is committed to git. Any third party can verify reproducibility by running the same selection logic against the same dataset version and confirming the hash matches.

### Inference environment

| Field | Value |
|---|---|
| Python | 3.11.x (conda env `spinphase_gw` on Windows) |
| torch | 2.10.0 (pytorch channel; CPU build) |
| transformers | 5.8.0 |
| datasets | 4.8.5 |
| huggingface-hub | 1.13.0 |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` (set during execution to allow OpenMP runtime coexistence) |

Inference processed at ~21 examples/second on CPU. Total runtime for 5,000 examples: ~4 minutes.

---

## Lock and Provenance

| Item | Reference |
|---|---|
| Pre-registration document | `case_studies/toxic_bert/PRE_REGISTRATION_TOXIC_BERT_v1.md` |
| Pre-registration / pipeline lock commit | git `1cca213` (2026-05-06) |
| Analysis script | `case_studies/toxic_bert/toxic_bert_calibration.py` (frozen at `1cca213`) |
| Materialized test subsample | `case_studies/toxic_bert/civil_comments_validation_subsample.csv` (SHA-256 `647436da…`) |
| Model revision (HF commit hash) | `4d6c22e74ba2fdd26bc4f7238f50766b045a0d94` |
| Per-example predictions | `case_studies/toxic_bert/predictions.csv` (committed at `f0d6833`, 2026-05-06) |
| Per-bin reliability scores | `case_studies/toxic_bert/calibration_scores.csv` (committed at `f0d6833`) |
| Aggregate calibration summary | `case_studies/toxic_bert/calibration_summary.json` (committed at `f0d6833`) |
| This result document commit | (recorded after committing) |

Per pre-registration Section 11, the methodology was bound at lock commit `1cca213` before any inference was run; the score vector was committed at `f0d6833` before this result document was drafted; the test outcome is published irrespective of whether it is favorable to the audited model.

This is the second public case study under the AI calibration verification methodology series. The first was `distilbert-sst2-calibration-v1` (locked at commit `dffd06a`, [result document](https://github.com/earldixon310-max/dynametrix/blob/master/docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md)).

---

*End of Toxic-BERT Calibration Verification v1 Outcome.*