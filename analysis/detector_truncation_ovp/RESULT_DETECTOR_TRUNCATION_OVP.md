# RESULT — DETECTOR_TRUNCATION_OVP (candidate study; lock 2) — OVP's first real ledger verdict

**Study:** DETECTOR_TRUNCATION_OVP — does the candidate observable **`truncated`** add Held-out Discriminative Gain (HDG) beyond the baseline **`confidence`** in predicting ChatGPT-detector correctness? (Lock 2 of the detector two-lock arc.)
**Governing spec:** OVP v0.1 @ signed tag `ovp-v0.1-lock`.
**Lock:** signed tag `detector-truncation-ovp-lock` (pre-reg + `judge_truncation.py` + `materialization_manifest_detector_truncation.json`; **two clean cold passes on byte-identical artifacts**, warm pass clean).
**Execution:** single run, master seed `0x77C0DE`, `R = 200` paired stratified splits, 2026-06-08 UTC; outputs at signed tag `detector-truncation-ovp-result`.
**Citation gate:** citable only after this document's own cold cross-pass (spec §7).

---

## Verdict: **INCONCLUSIVE**

| Quantity | Value |
|---|---|
| **`D` = median(HDG_AUC[1..200])** | **0.029333626486377606** |
| Inherited band `[τ_lo, τ_hi]` | `[0.024589, 0.068291]` (provenance `detector-ovp-calib-result`) |
| Band relation | `τ_lo ≤ D ≤ τ_hi` → **Inconclusive** (`D > τ_hi`: false; `D < τ_lo`: false; `D in band`: true) |

`D` falls in the pre-registered **closed ambiguity band** `[τ_lo, τ_hi]`: `truncated` adds *more* than the noise floor (`D > τ_lo`) but does **not** reach the "weakest meaningful signal" bar (`D < τ_hi`). Per spec §6 this is an **abstention** — the instrument completing without placing the candidate cleanly on either side of the binary — recorded with the same parity as any Validated or Not-Validated result.

This is **OVP's first verdict on a real candidate.** It advances OVP from *self-validated + first-real-calibration* toward the **operational** rung (spec §6: ≥3 real ledger verdicts of any outcome; this is **1 of 3**).

## The numbers (auditable from `detector_truncation_results.json` under the pinned numpy `'linear'` rule)

- **HDG_AUC distribution over 200 paired splits:** min **+0.0055**, P5 **+0.01882**, **median +0.02933**, mean **+0.02909**, P95 **+0.03853**, max **+0.0446**.
- **All 200 replications are positive** (`truncated` reliably adds a small gain), **0 of 200 reach `τ_hi`**, and **155/200 (77.5%) land in the band**, 45/200 (22.5%) below `τ_lo`, 0/200 above `τ_hi`.
- **Median ≈ mean (0.02933 vs 0.02909)** — the pinned `D = median` is *not* decision-relevant here: the mean would also fall in the band → Inconclusive. The choice is auditable from the persisted distribution and does not change the verdict.
- Error-class **AP** sensitivity panel (non-gating): median **+0.02014**, consistent small positive.
- Substrate: n = 2000, errors = 644, `truncated` prevalence **0.1155** (231 of 2000).

## Interpretation (mechanism-agnostic, per v0.1)

`truncated` has a **strong marginal** association with correctness — on the frozen materialization, accuracy is **0.848 on truncated inputs vs 0.656 on untruncated** (a 19.3-point gap; source `detector_per_example.csv`). Yet its **incremental** gain *beyond confidence* is small and sub-threshold (median ΔAUC 0.029). The natural reading is that **the detector's own confidence already encodes most of what truncation signals about its reliability** — so once confidence is in the model, knowing an input was truncated adds only a little.

v0.1's single measure is **mechanism-agnostic** and deliberately cannot say *why* the incremental gain is small — whether `truncated` is largely *redundant* with confidence or *weakly additive*. That redundant-vs-additive distinction is precisely v0.2's job (the four-verdict structure). What v0.1 records here is the honest binary-abstention: a real, reliably-positive, but sub-validation-bar effect. Note the verdict is **not** Not-Validated — `D` sits clearly above `τ_lo` (78% of replications exceed it) — so the candidate is not in the "no demonstrated structure" bucket; it is genuinely in the ambiguity zone.

## What this establishes / does not

- **Does:** issue OVP's first real candidate verdict — `truncated` is **Inconclusive** as an addition to detector confidence under the pinned standardized-linear estimator, judged against externally-frozen cut points; record it as the first OVP ledger row with full parity.
- **Does not:** decide whether `truncated` is scientifically interesting or useful (spec §0); separate redundant-from-additive (v0.2); generalize beyond this substrate/estimator/metric (a verdict can flip under a nonlinear estimator — that would be a separate, legitimately-recorded question); or, on its own, reach the operational rung (needs ≥3 real verdicts; this is the first).

## Ledger row (spec §5)

| field | value |
|---|---|
| candidate | `truncated` (input exceeded the detector's 512-token window) |
| baseline | `confidence` (max softmax) |
| substrate | ChatGPT-detector RoBERTa (`d2b342c6…`) over RAID test subsample (`a29f8f2c…`), n=2000 |
| measure `D` | median HDG via AUC; standardized L2 logistic; stratified 50/50 paired × 200; seed `0x77C0DE` |
| cut points | `τ_lo=0.024589`, `τ_hi=0.068291`; provenance `detector-ovp-calib-result` (external pre-lock calibration) |
| **verdict** | **Inconclusive** (`D=0.029334` ∈ `[τ_lo, τ_hi]`) |
| cross-pass | warm clean (Ancestry fix); 2/2 cold clean on byte-identical artifacts (`CROSSPASS_DETECTOR_TRUNCATION_OVP.md`) |

## Provenance

Inherited per-example `detector_per_example.csv` sha256 `24dac078…01afc643` (verified at run via the hardcoded anchor; no model re-run); cut points asserted byte-identical to `detector_calibration_results.json` at runtime (`verify_cut_points`) and lock (manifest); model `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c6…`; dataset `a29f8f2c…`; estimator `StandardScaler(train-fit) → LogisticRegression(lbfgs, C=1.0, max_iter=1000, fit_intercept=True)`; seed `0x77C0DE` (= canonical), R = 200 (= canonical); environment per `materialization_manifest_detector_truncation.json` (Python 3.12.10, numpy 2.1.2, scikit-learn 1.8.0). Full per-replication HDG distribution (AUC + error-class AP, 200) persisted under `hdg_distribution` — every figure above is checkable from the frozen artifacts alone.
