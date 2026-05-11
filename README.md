# Pre-registered Evaluation Repository

This repository holds a public record of pre-registered, cryptographically-locked evaluations of probabilistic models. Each evaluation specifies its methodology and decision criteria in writing before any prediction is computed, commits the methodology and analysis code to git at a fixed hash, executes once under a frozen pipeline, and publishes the result irrespective of outcome.

The repository functions as a working artifact: anyone may clone it, check out any locked commit, and reproduce the evaluation end-to-end from the same data, code, and parameters that produced the published result.

---

## Evaluations on record

| Identifier | Domain | Pre-registration | Result | Outcome |
|---|---|---|---|---|
| `pre-registration-v1` | Severe weather forecasting (calibrator-v1.0) | [docs/PRE_REGISTRATION_v1.md](docs/PRE_REGISTRATION_v1.md) | — | No predictive skill; static-input limitation disclosed up front |
| `pre-registration-v2` | Severe weather forecasting (calibrator-v2.0, atmospheric inputs) | [docs/PRE_REGISTRATION_v2.md](docs/PRE_REGISTRATION_v2.md) | — | No predictive skill at 50 km radius |
| `verification-v3a-spatial-100km` | Severe weather forecasting (re-scored at 100 km) | [docs/PRE_REGISTRATION_v3a.md](docs/PRE_REGISTRATION_v3a.md) | [docs/RESULT_v3a_2026-05-04.md](docs/RESULT_v3a_2026-05-04.md) | Hypothesis falsified; BSS = −0.31 |
| `pre-registration-v3` | Severe weather forecasting (calibrator-v3.0, richer inputs) | [docs/PRE_REGISTRATION_v3.md](docs/PRE_REGISTRATION_v3.md) | — | Forward-only verification: 36 predictions accumulated 2026-05-04 18:57Z to 23:05Z, then operational dormancy until 2026-05-09. Continuous accumulation resumed; first meaningful verification window approximately 2026-05-26. Gap will be documented in the eventual result document. |
| `spinphase-gw-blind-v1` | Gravitational-wave detection (GW150914 blind ranking) | [docs/PRE_REGISTRATION_GW_v1.md](docs/PRE_REGISTRATION_GW_v1.md) | [docs/RESULT_GW_v1_2026-05-04.md](docs/RESULT_GW_v1_2026-05-04.md) | R = 52 of 100; no detection capability under this test |
| `spinphase-gw-quietwell-v1` | Gravitational-wave detection (within-segment differential) | [docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md](docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md) | [docs/RESULT_GW_QUIETWELL_v1_2026-05-04.md](docs/RESULT_GW_QUIETWELL_v1_2026-05-04.md) | R_D = 50 of 100; no local emergence under this test |
| `distilbert-sst2-calibration-v1` | AI/ML model calibration (DistilBERT SST-2) | [case_studies/distilbert_sst2/PRE_REGISTRATION_DISTILBERT_SST2_v1.md](case_studies/distilbert_sst2/PRE_REGISTRATION_DISTILBERT_SST2_v1.md) | [docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md](docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md) | Not calibrated; bimodal overconfidence at the extremes |
| `toxic-bert-calibration-v1` | AI/ML model calibration (Unitary Toxic-BERT, Civil Comments) | [case_studies/toxic_bert/PRE_REGISTRATION_TOXIC_BERT_v1.md](case_studies/toxic_bert/PRE_REGISTRATION_TOXIC_BERT_v1.md) | [docs/RESULT_TOXIC_BERT_v1_2026-05-06.md](docs/RESULT_TOXIC_BERT_v1_2026-05-06.md) | Calibration drift detected; structured overconfidence in middle-to-high probability range |

Seven evaluations executed under the protocol; seven locked outcomes; one further evaluation accumulating data for future verification. Every result document is bound at the commit recorded in its provenance section and is not subject to revision after lock.

---

## Methodology

Every evaluation in this repository is conducted under the following protocol:

1. **Pre-registration.** A document specifies the model or system under test, the data, the pipeline, the metrics, the decision criteria, and the conditions under which each possible outcome would be recorded. The document is signed and committed to git before any prediction or score is computed.
2. **Cryptographic lock.** The pre-registration, the analysis code, and (where applicable) the test data are committed to git in a single lock commit. SHA-256 hashes are computed for any held-out artifacts (sealed keys, blinded populations) and committed alongside the methodology so that post-hoc tampering is detectable. The lock commit hash is recorded in the result document.
3. **Frozen execution.** The analysis code is not modified between the lock commit and the recording of all outputs. Hashes are verified at runtime; the script refuses to execute against modified data. Re-runs for reproducibility are permitted; revisions to outputs are not.
4. **Publication of outcome.** The result document records the outcome under the pre-registered classification, including the cases where the outcome is unfavorable to the system being evaluated. Result documents are bound at commit time and may not be revised. The canonical structure of result documents is documented in [docs/RESULT_TEMPLATE.md](docs/RESULT_TEMPLATE.md); the canonical structure of pre-registrations for AI/ML calibration audits is documented in [docs/PRE_REGISTRATION_AI_CALIBRATION_TEMPLATE.md](docs/PRE_REGISTRATION_AI_CALIBRATION_TEMPLATE.md).

The protocol is portable across domains: the eight evaluations on record include severe weather forecasting verification against ground-truth storm reports, gravitational-wave detection on LIGO open data, and probabilistic model calibration on public natural-language classifiers. The same discipline applies in each case.

---

## Most recent case study

`distilbert-sst2-calibration-v1` evaluated `distilbert-base-uncased-finetuned-sst-2-english` (HuggingFace revision `714eb0fa…`) for calibration on the SST-2 validation split (872 examples). The pre-registered claim was that across 10 reliability bins, the model's predicted probabilities would fall within Wilson 95% confidence intervals of observed positive-class frequencies for at least 8 of 10 bins, alongside a positive Brier skill score against base-rate climatology.

Outcome: **not calibrated**. The model's accuracy on SST-2 validation is 91.06%, matching the model card. The Brier skill score is +0.667. But of the 2 reliability bins meeting the n ≥ 30 sample-size requirement, neither passed the Wilson criterion. When the model predicts 99.6% confidence, the actual positive-class frequency at that confidence level is 90.9% — an 8.7-percentage-point overconfidence. When the model predicts 0.65% probability, the actual positive rate is 6.1%.

The model is bimodal and systematically overconfident at both extremes. A user thresholding on confidence ≥ 0.95 expecting 95% precision will instead see something close to 91%. The accuracy claim and the calibration claim point at different downstream use-cases.

The full result, including the per-bin reliability table, decision-criterion application, and an itemized list of what the test does and does not falsify, is at [docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md](docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md).

---

## Reproducing a result

Each evaluation is reproducible end-to-end from the locked commit. To reproduce `distilbert-sst2-calibration-v1`:

```
git clone https://github.com/earldixon310-max/dynametrix.git
cd dynametrix
git checkout dffd06a    # the lock commit for the DistilBERT result
cd case_studies/distilbert_sst2
python -m pip install -r requirements.txt
python distilbert_sst2_calibration.py run
```

The script verifies the data SHA-256, downloads the pinned HuggingFace model revision, runs inference on the locked test set, computes the pre-registered calibration metrics, and writes outputs under the same names as those committed at `2f8bb9e`. A successful run produces calibration values numerically equivalent to the published result within float32 precision.

The same procedure applies to the other evaluations in this repository, with the analysis path adjusted to each evaluation's directory and lock commit.

---

## Requesting an evaluation

The methodology is offered as an independent service for organizations that have a probabilistic model and a need to defend specific claims about it — calibration, generalization, subgroup behavior, robustness. Each engagement begins with a written pre-registration agreed by both parties, followed by a frozen execution and a published outcome under the same protocol used in the evaluations above.

A first engagement is typically scoped to one model, one specific claim, and a held-out test dataset, with a 2–4 week timeline from agreement to delivery. Engagement details and pricing for a pilot are available on request.

To inquire: earl_dixon@hsagconsortium.com

---

## Provenance

This repository is maintained by Earl Dixon. The methodology has been applied across three scientific and applied domains over the period April–May 2026. All evaluations recorded above were executed under the protocol described in the *Methodology* section, with no exceptions, and all outcomes were locked at commit time.

Inquiries regarding methodology, reproduction failures, or proposed evaluations are welcome.