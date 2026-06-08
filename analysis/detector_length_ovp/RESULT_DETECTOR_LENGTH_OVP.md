# RESULT — DETECTOR_LENGTH_OVP (candidate study; OVP real candidate #2)

**Study:** DETECTOR_LENGTH_OVP — does **`text_length`** (full token count under the detector's tokenizer) add Held-out Discriminative Gain beyond **`confidence`** in predicting ChatGPT-detector correctness? Second real candidate on the ChatGPT-detector substrate, judged against the same locked calibration band.
**Governing spec:** OVP v0.1 @ `ovp-v0.1-lock`.
**Lock:** signed tag `detector-length-ovp-lock` (pre-reg + `judge_length.py` + manifest; **two clean cold passes on byte-identical artifacts**).
**Execution:** single run, master seed `0x73C0DE`, `R = 200` paired stratified splits, 2026-06-08 UTC; outputs at signed tag `detector-length-ovp-result`.
**Citation gate:** citable only after this document's own cold cross-pass (spec §7).

---

## Verdict: **NOT-VALIDATED**

| Quantity | Value |
|---|---|
| **`D` = median(HDG_AUC[1..200])** | **−0.011777652576998476** |
| Inherited band `[τ_lo, τ_hi]` | `[0.024589, 0.068291]` (provenance `detector-ovp-calib-result`) |
| Band relation | `D < τ_lo` → **Not-Validated** (`D < τ_lo`: true; in band: false; `> τ_hi`: false) |

`D` falls **below `τ_lo`**: `text_length` adds **no demonstrated out-of-sample structure beyond confidence** under the pinned estimator — and the negative median means adding it slightly *reduces* held-out AUC on average. Per spec §6 this is **Not-Validated**, deliberately **mechanism-agnostic** (it covers both *redundant-with-confidence* and *noise-like*; v0.1's single measure cannot separate them — that is v0.2's job). Recorded with full parity. This is **OVP real candidate verdict #2** (§6 ladder: **2 of 3** toward operational).

## The numbers (auditable from `detector_length_results.json` under the pinned numpy `'linear'` rule)

- **HDG_AUC distribution over 200 paired splits:** min **−0.0532**, P5 **−0.04429**, **median −0.01178**, mean **−0.01355**, P95 **+0.01335**, max **+0.0419**.
- **199 of 200 replications below `τ_lo`** (`frac_below_tau_lo = 0.995`); 1/200 in band; **0/200** above `τ_hi`; **79% strictly negative.** Decisively below the floor.
- **Median ≈ mean** (−0.01178 vs −0.01355) — the `D = median` pin is not decision-relevant (the mean is also below `τ_lo` → Not-Validated).
- Error-class **AP** sensitivity panel (non-gating; never enters the verdict): median **−0.00319**, consistent small negative.
- `text_length` range: min **38**, median **313**, max **3510** tokens; n = 2000, errors = 644.
- **Materialization cross-check passed:** `1[text_length>512]` reproduced the inherited `truncated` column exactly (the run proceeded to judging; it would have aborted otherwise). `text_length` sha `35aa2c41…f13a19`.

## Interpretation (mechanism-agnostic, per v0.1)

`text_length` has only a **weak, non-monotonic marginal** association with correctness (Pearson r = **0.090**; quartile accuracies **0.634 / 0.741 / 0.700 / 0.637** — a hump peaking at middling lengths). The pinned **linear** standardized estimator can only use a feature monotonically, so it cannot capture a hump; beyond confidence, the linear length term contributes overfitting noise, which is why the held-out gain is **negative**. The natural reading: **confidence is approximately a sufficient statistic for the smooth length-related uncertainty** — the detector's own confidence already reflects length-appropriate doubt across the range, so raw length adds nothing.

**Read against verdict #1:** `truncated` (the discrete `>512` ceiling indicator) was Inconclusive with a small *positive* `D` (+0.029); `text_length` (the continuous parent across the full range) is Not-Validated with a *negative* `D` (−0.012). So the only whisper of residual reliability signal beyond confidence sits at the **discrete truncation regime**, not in **continuous length** — consistent with truncation being an information-loss event the binary flag isolates cleanly, while smooth length is already absorbed by confidence.

**Estimator-conditional caveat (spec §0/§9).** This verdict is conditional on the pinned **linear** instantiation. The non-monotonic (hump-shaped) marginal means a **nonlinear** estimator could plausibly extract length structure — a *separate, legitimately-recorded* question, not a contradiction (a candidate Not-Validated under a linear estimator and Validated under a nonlinear one are two different questions per spec §0). v0.1 reports only what the pinned linear measure supports.

## What this establishes / does not

- **Does:** issue OVP's second real verdict — `text_length` is **Not-Validated** as an addition to detector confidence under the pinned standardized *linear* estimator, judged against externally-frozen cut points; record it with parity; and, with verdict #1, characterize the detector's confidence-as-sufficient-statistic property (holds for smooth length; a sliver of residual signal only at the discrete truncation ceiling).
- **Does not:** decide `text_length`'s scientific interest/use; separate redundant-vs-noise (v0.2); generalize beyond this substrate/estimator/metric — in particular says nothing about a *nonlinear* estimator; reach operational alone (this is #2 of ≥3).

## Ledger row (spec §5)

| field | value |
|---|---|
| candidate | `text_length` (full token count under the detector tokenizer) |
| baseline | `confidence` (max softmax) |
| substrate | ChatGPT-detector RoBERTa (`d2b342c6…`) over RAID test subsample (`a29f8f2c…`), n=2000 |
| measure `D` | median HDG via AUC; standardized L2 logistic; stratified 50/50 paired × 200; seed `0x73C0DE` |
| cut points | `τ_lo=0.024589`, `τ_hi=0.068291`; provenance `detector-ovp-calib-result` |
| **verdict** | **Not-Validated** (`D=−0.011778 < τ_lo`) |
| cross-pass | 2/2 cold clean on byte-identical artifacts (`CROSSPASS_DETECTOR_LENGTH_OVP.md`) |

## Provenance

`B,y,truncated` inherited byte-identical from the calibration-locked `detector_per_example.csv` sha `24dac078…01afc643` (hash-verified; no model re-run); `text_length` materialized by the single run via the pinned tokenizer (`Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c6…`, no model inference) over dataset `a29f8f2c…`, cross-checked against the inherited `truncated`; `detector_length_per_example.csv` sha `35aa2c41…f13a19`. Cut points asserted byte-identical to the calibration result at runtime (`verify_cut_points`) and lock (manifest). Estimator `StandardScaler(train-fit) → LogisticRegression(lbfgs, C=1.0, max_iter=1000, fit_intercept=True)`; seed `0x73C0DE` (= canonical), R = 200 (= canonical); environment per `materialization_manifest_detector_length.json` (Python 3.12.10, numpy 2.1.2, scikit-learn 1.8.0, transformers 5.9.0). Full per-replication HDG distribution (AUC + error-class AP, 200) persisted under `hdg_distribution`.
