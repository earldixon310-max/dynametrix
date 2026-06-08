# RESULT — DETECTOR_DIRECTION_OVP (candidate study; OVP real candidate #3) — OVP reaches OPERATIONAL

**Study:** DETECTOR_DIRECTION_OVP — does **`predicted_prob_ai`** (the detector's raw *directional* probability) add Held-out Discriminative Gain beyond the *folded* baseline **`confidence`** (`max(p,1−p)`) in predicting ChatGPT-detector correctness? Third real candidate on the ChatGPT-detector substrate.
**Governing spec:** OVP v0.1 @ `ovp-v0.1-lock`.
**Lock:** signed tag `detector-direction-ovp-lock` (pre-reg + `judge_direction.py` + manifest; **two clean cold passes on byte-identical artifacts**, warm pass clean, after the §3/§9 ancestry correction).
**Execution:** single run, master seed `0xDEC0DE`, `R = 200` paired stratified splits, 2026-06-08 UTC; outputs at signed tag `detector-direction-ovp-result`.
**Citation gate:** citable only after this document's own cold cross-pass (spec §7).

---

## Verdict: **INCONCLUSIVE** — and OVP reaches the **operational** rung (§6.2)

| Quantity | Value |
|---|---|
| **`D` = median(HDG_AUC[1..200])** | **0.026445610949266120** |
| Inherited band `[τ_lo, τ_hi]` | `[0.024589, 0.068291]` (provenance `detector-ovp-calib-result`) |
| Band relation | `τ_lo ≤ D ≤ τ_hi` → **Inconclusive** (margin above `τ_lo`: **+0.00186**) |

`D` falls in the pre-registered closed band — **a borderline Inconclusive**, barely above the noise floor (`D − τ_lo = +0.0019`; **44.5% of replications fall below `τ_lo`**). Under the pinned *linear* estimator, the raw directional probability adds only a small, ambiguous gain beyond folded confidence along the **slope-asymmetry axis `[B,p]` spans**. Per spec §6 this is an abstention, recorded with parity.

**This is OVP's third real candidate verdict — reaching the operational rung** (§6.2: self-validated + ≥3 real ledger verdicts of any outcome). The ledger: `truncated` Inconclusive, `text_length` Not-Validated, `predicted_prob_ai` Inconclusive — three honest non-positives, no false positive in three real audits.

## The numbers (auditable from `detector_direction_results.json`, pinned numpy `'linear'` rule)

- **HDG_AUC distribution (200 paired splits):** min **−0.0043**, P5 **+0.0034**, **median +0.02645**, mean **+0.02505**, P95 **+0.0425**, max **+0.0541**. 97% positive, but **0/200 reach `τ_hi`** and **44.5% below `τ_lo`** (55.5% in band) → borderline.
- **Median ≈ mean** (+0.02645 vs +0.02505) — the `D = median` pin is not decision-relevant (mean also in band → Inconclusive).
- Error-class **AP** (non-gating): median **+0.0042**, small positive.
- n = 2000, errors = 644.

## Interpretation — the asymmetry is real but **intercept-level**, which the slope-axis candidate barely detects

The non-gating **per-predicted-class diagnostic** (computed once in the locked run) reveals a **large class-asymmetry in the detector's reliability**:

| predicted class | accuracy | n |
|---|---|---|
| predicts **AI** (`pred=1`) | **0.773** | 652 |
| predicts **Human** (`pred=0`) | **0.632** | 1348 |
| **gap** | **+0.141** (14.1 points) | — |

The detector is **far more reliable when it predicts AI than when it predicts Human** (and it predicts Human more often — 1348 vs 652 — so it is conservative and frequently wrong when it clears text as human, i.e. it misses AI). This is a **substantial asymmetry**. Yet the candidate verdict is only a borderline Inconclusive — because this asymmetry is overwhelmingly **intercept-level** (a base-rate shift in correctness by predicted class), and the `[B,p]` candidate under the linear estimator can only access direction through the **slope-coupled** term (one parameter `w_p` drives both); it **cannot cleanly represent a pure-intercept shift** (that would require `w_p = 0`). So `[B,p]` registers only a weak, near-floor gain.

This is exactly the **scoped reading the locked §3/§9 framing committed to**: an Inconclusive on `[B,p]` means **no strong slope-type class-asymmetry on the axis `[B,p]` spans** — and it explicitly does **not** rule out a pure-intercept asymmetry, which the diagnostic shows is in fact large. *(The pre-lock draft that called raw `p` "strictly more powerful" and a non-positive verdict a "symmetric null in both slope and intercept" was corrected before lock under cross-pass; this run's 14-point intercept gap would have directly contradicted that overstatement — the correction was borne out by the data.)*

**Estimator-conditional (spec §0/§9).** The verdict is conditional on the pinned linear estimator and the *folded-vs-directional* contrast. The intercept asymmetry the diagnostic reveals would be the natural target of a separate **`[B, pred]`-shaped** candidate study (the binary predicted-class direction), which — on this evidence — would plausibly **Validate**. That is a distinct, legitimately-recorded question, not a contradiction.

## What this establishes / does not

- **Does:** issue OVP's third real verdict (reaching operational); establish that the detector's **slope-type** class-asymmetry beyond folded confidence is, at most, borderline (Inconclusive) under the linear estimator; surface — via the non-gating diagnostic — a large **intercept-level** reliability asymmetry (AI-leaning 0.773 vs Human-leaning 0.632).
- **Does not:** decide scientific interest/use; separate redundant-vs-noise (v0.2); claim anything about a `[B,pred]` intercept-shaped study or a nonlinear estimator (both separate questions); reach community-validated (principal-operator-authored; §6.3 needs an external candidate).

## Ledger row (spec §5)

| field | value |
|---|---|
| candidate | `predicted_prob_ai` (raw directional probability) |
| baseline | `confidence` (folded `max(p,1−p)`) |
| substrate | ChatGPT-detector RoBERTa (`d2b342c6…`) over RAID test subsample (`a29f8f2c…`), n=2000 |
| measure `D` | median HDG via AUC; standardized L2 logistic; stratified 50/50 paired × 200; seed `0xDEC0DE` |
| cut points | `τ_lo=0.024589`, `τ_hi=0.068291`; provenance `detector-ovp-calib-result` |
| **verdict** | **Inconclusive** (`D=0.026446 ∈ [τ_lo, τ_hi]`, borderline) |
| cross-pass | warm clean; 2/2 cold clean on byte-identical (corrected) artifacts (`CROSSPASS_DETECTOR_DIRECTION_OVP.md`) |

## Provenance

`B,y,predicted_prob_ai,pred` inherited byte-identical from the calibration-locked `detector_per_example.csv` sha `24dac078…01afc643` (hash-verified; **no materialization, no model run**); cut points asserted byte-identical to `detector_calibration_results.json` at runtime (`verify_cut_points`) and lock (manifest); model `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c6…`; dataset `a29f8f2c…`; estimator `StandardScaler(train-fit) → LogisticRegression(lbfgs, C=1.0, max_iter=1000, fit_intercept=True)`; seed `0xDEC0DE` (= canonical), R = 200 (= canonical); environment per `materialization_manifest_detector_direction.json` (Python 3.12.10, numpy 2.1.2, scikit-learn 1.8.0). Full per-replication HDG distribution (AUC + error-class AP, 200) persisted under `hdg_distribution`.
