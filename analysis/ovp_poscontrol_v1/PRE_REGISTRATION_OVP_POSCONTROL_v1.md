# Pre-Registration — OVP_POSCONTROL_v1

**Study type:** OVP instrument-validation study (positive control).
**Governing spec:** OVP — Observable Validation Protocol, **v0.1**, locked at signed tag **`ovp-v0.1-lock`** (verified-good SSH signature). **Note on the lock (important for verification):** OVP v0.1 was locked **tag-only / byte-exact** — the spec *body* deliberately retains its "working draft — not locked" status line so the locked artifact stays byte-identical to the version its cold reader cleared; the authoritative lock is carried by the signed tag, `OVP_v0.1_LOCK_NOTICE.md`, and `OVP_DESIGN_HISTORY.md`, not by the body's status line (verify via `git tag -v ovp-v0.1-lock`). This study conforms to the spec at that tag without modification; where this document and the spec appear to differ, the spec governs and this document is wrong.
**Status:** DRAFT — **not locked.** The cut points are frozen from the calibration result (§5.1; calibration `ovp-poscontrol-v1-calib-lock` / `ovp-poscontrol-v1-calib-result`). Locking follows the §10 sequence: two independent cold passes (which the author cannot clear), then a single atomic lock commit and one run. **This document deliberately does not narrate its own review-progress** (such status goes stale); current progress is tracked in `CROSSPASS_OVP_POSCONTROL_v1.md`, outside this artifact. No code runs until lock.

---

## 1. Objective and what passing means

OVP_POSCONTROL_v1 is OVP's own positive control: it runs the locked v0.1 decision rule (HDG against two pinned cut points → one of three verdicts) over synthetic arms whose correct verdicts are known by construction, and checks that the rule returns them at pre-committed rates.

Per the spec's §6 maturity ladder, **passing this study moves OVP from nothing to the first rung — "self-validated."** It does *not* make OVP operational or community-validated (those require real ledger verdicts and an externally-authored candidate). Until this study passes, no candidate-observable verdict produced under OVP may be cited as established. This study is the gate, and nothing more than the gate.

A **PASS** requires all three gated per-arm bars (§7) to be met **and** all setup controls (§8) to hold. Anything else is reported honestly as a FAIL or a near-miss, with no reseeding, no softened threshold, no widened band (AEPF single-execution + null-parity discipline).

---

## 2. The measure (HDG) — instantiation pinned for this study

The version fixes the *measure* (HDG); this study pins the *instantiation* (spec §1, "two levels kept distinct"):

- **Discrimination metric:** ROC **AUC** on a held-out split. AUC is natively higher-is-better and bounded in [0,1], so the spec's orientation requirement (§1) holds without negation.
- **Estimator / function class:** L2-regularized **logistic regression** (scikit-learn `LogisticRegression`, `solver='lbfgs'`, `C=1.0`, `max_iter` fixed, no class weighting). Pinned as a load-bearing element, not an implementation detail.
- **Held-out split protocol:** a single **stratified 50/50 train/test split** per replication. Baseline and candidate models are fit on the *same* train split and scored on the *same* test split, so the only difference between them is the presence of `C` (no leakage between the two models' data).
- **HDG per replication:** `D = AUC_test(logistic[B, C]) − AUC_test(logistic[B])`.
- **N per replication:** 4000 samples (2000 train / 2000 test).
- **Replications:** `R = 100` (spec-fixed for OVP_POSCONTROL_v1), under **one master seed** `0xFACADE`; per-replication seeds are derived from it via NumPy `SeedSequence` (one spawned child per replication, in index order), as implemented in the locked `validate_ovp.py`.

This HDG instantiation (metric, estimator, split, `N`) is **identical to and inherited from the calibration study** (`PRE_REGISTRATION_OVP_POSCONTROL_v1_CALIB.md` §3), which locks first and sets the HDG scale; only the seed differs (`0xFACADE` here vs `0xCA11B` there). The positive control does not redefine the instantiation — the dependency runs calibration → positive control only.

The verdict for a single replication is the spec's deterministic rule: `D > τ_hi → Validated`; `D < τ_lo → Not-Validated`; `τ_lo ≤ D ≤ τ_hi → Inconclusive`. Nothing else enters the verdict (spec §3).

---

## 3. Substrate and generative model

Per replication, draw `N` i.i.d. samples from:

- Latent signals `s1, s2 ~ Normal(0, 1)`, independent.
- Target `y ~ Bernoulli(sigmoid(β1·s1 + β2·s2))`, intercept 0. (`β2` is the scalar coefficient on `s2` in the y-model — **not** a product with the outcome `y`.)
- **Baseline observable** `B = s1 + Normal(0, σ_B²)` — a single noisy window onto `s1` only. `B` carries no information about `s2`.

`s2` is the structure the baseline *cannot* recover (it is independent of `s1` and of `B`). Whether the **candidate** `C` carries `s2` is what distinguishes the arms.

**Pinned generative constants** (defaults; confirm before lock): `β1 = 1.0`, `β2 = 1.0`, `σ_B = 1.0` — all fixed substrate constants. `β1` and `σ_B` set the baseline's own predictive strength (the §8 setup control verifies non-degeneracy, `AUC(B) > 0.60`); `β2 > 0` is what makes `s2` genuine structure that a candidate observing it can add. The **candidate-side** observation parameters — `σ_C` (Arm 1) and `σ₃` (Arm 3) — are set by the calibration sweeps (§5) so those arms land where intended relative to the frozen band, and are now **frozen from the calibration result**: `σ_C = 2.0` (Arm 1), `σ₃ = 4.0` (Arm 3) — see the frozen-values block, §5.1.

---

## 4. The four arms (constructions pinned)

Each arm fixes how `C` is generated. "Expected `D`" placement is distributional (spec §4): the construction pins the *distribution* of `D` on the correct side of the band; the per-arm bar measures realized landings under sampling scatter.

| Arm | Candidate `C` | Carries `s2`? | Recoverable from `B`? | Expected `D` | Correct v0.1 verdict |
|---|---|---|---|---|---|
| **1 — Known-meaningful** | `C = s2 + Normal(0, σ_C²)`, `σ_C = 2.0` | yes (full) | no | above `τ_hi` (+0.0104 margin) | **Validated** |
| **2 — Deterministic-redundant** | `C = 2·B − 0.5` (deterministic affine of `B`) | no | yes (exactly) | below `τ_lo` | **Not-Validated** |
| **3 — Partial-redundancy** | `C = B + s2 + Normal(0, σ₃²)`, `σ₃ = 4.0` | partial (noisy `s2`) | partly | targets band midpoint | (non-gated; band witness) |
| **4 — Pure-noise** | `C = Normal(0, 1)`, independent of everything | no | no | below `τ_lo` (≈ 0) | **Not-Validated** |

Rationale per arm:
- **Arm 1** adds an independent predictive dimension the baseline cannot see, so the augmented model gains real out-of-sample AUC → positive HDG. `σ_C` and the candidate signal strength are set by the calibration sweep so Arm 1's distribution sits clearly above `τ_hi`.
- **Arm 2** is a deterministic affine function of `B`: it is perfectly recoverable from `B` and carries zero incremental information about `y`. Under the pinned estimator the augmented model gains nothing out-of-sample → HDG ≈ 0 (slightly negative from fitting a redundant parameter). The textbook "baseline in a costume."
- **Arm 3** is mostly `B` plus a **noise-attenuated** `s2` increment, its strength set by the noise level `σ₃` (chosen from the calibration partial sweep, §5, to target the band midpoint). The increment is controlled by *noise*, not scale: the linear estimator is scale-invariant, so a scaled clean `s2` would not control HDG — only added noise attenuates the recoverable signal. Non-gated; its output is the full verdict distribution (band occupancy primary).
- **Arm 4** is independent noise: no information about `y` or `B`, so HDG ≈ 0 out-of-sample.

Arms 2 and 4 both correctly return **Not-Validated** and are deliberately undifferentiated as to mechanism (redundant vs noise) — that distinction is OVP v0.2, not v0.1 (spec §4).

---

## 5. Cut-point calibration study (separate, pre-lock, own seed) — the bootstrap

Per spec §1 ("Bootstrap path for the first study under a new measure"), the cut points come from a **separate calibration study**, run and locked **before** the positive control, under its **own seed `0xCA11B`** (distinct from the positive control's `0xFACADE`), on **distinct data draws** — never the positive control's own arms, and never the noise arm it must later clear.

**Constructions (siblings of, not identical to, the arms; own seed):**
- **Null-redundant:** `C = 2·B − 0.5` (same form as Arm 2 but its own draws).
- **Null-noise:** `C = Normal(0,1)` independent (same form as Arm 4 but its own draws).
- **Meaningful sweep:** `C = s2 + Normal(0, σ_C²)` swept over `σ_C` (candidate observation noise; smaller `σ_C` = cleaner view of `s2` = stronger signal), to map HDG vs. candidate strength. This mapping sets Arm 1's `σ_C`; Arm 3's `σ₃` comes from a separate partial sweep (below), relative to the frozen band.

`R_cal = 200` replications per construction (more than the positive control, for stable percentile estimates), `N = 4000`, same metric/estimator/split as §2.

**Rule for setting the cut points (pinned here; values produced by the calibration run):**
- `τ_lo` = **`max( 95th-pct(null-redundant), 95th-pct(null-noise) )`** — the higher of the two null types' 95th percentiles, **not** a pooled 95th. The two nulls have different finite-sample HDG behavior (the affine-redundant null can sit slightly negative under L2 fitting; the independent-noise null centers cleanly at 0), and pooling could let one null's heavier upper tail hide under the mixture. Taking the max places `τ_lo` above the 95th percentile of *each* null type separately, so neither null arm creates false-validate risk through asymmetric tails. It is strictly positive (a high quantile of near-zero distributions) and places ~95% of each null-like candidate below it.
- `τ_hi` = chosen from the meaningful sweep as the HDG value clearly separated above `τ_lo` such that a known-meaningful candidate at Arm 1's pinned strength exceeds it in ≥95% of calibration draws (giving Arm 1 margin to clear its ≥90/100 bar). Operationally: pick the sweep point whose 5th-percentile HDG `> τ_lo` by a margin, set `τ_hi` to that 5th percentile, and pin Arm 1's strength to that sweep point.
- `σ₃` for Arm 3 = the partial-sweep noise level (`C = B + s2 + Normal(0, σ₃²)`) whose **median** HDG falls nearest the **midpoint** of `[τ_lo, τ_hi]` — noise-attenuated, not scaled (the linear estimator is scale-invariant, so a scaled clean `s2` would not control HDG).

**Hard separability check (calibration setup control):** after the calibration run, require `0 < τ_lo < τ_hi` with a non-trivial gap. **If the null and meaningful distributions overlap such that no valid band exists, the design is mis-specified** — it is documented as such and revised under a new lock, never fudged into a band. The calibration study is locked under its own tag (`ovp-poscontrol-v1-calib-lock`) with its outputs (`τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃`) frozen into the positive-control pre-registration before *its* lock.

### 5.1 Frozen cut points and arm parameters (from the calibration result)

The calibration study was drafted, cleared by **two independent cold passes** on byte-identical artifacts, locked at signed tag **`ovp-poscontrol-v1-calib-lock`**, and **run once** under seed `0xCA11B`. Its single-execution result is recorded at signed tag **`ovp-poscontrol-v1-calib-result`** (commit `2131679`, `calibration_results.json`) and returned **`USABLE BAND`** — all four separability checks passed. The following values are therefore **frozen** for this positive control and may not change without a new lock:

| Parameter | Frozen value |
|---|---|
| `τ_lo` (lower cut point) | **0.000852** |
| `τ_hi` (upper cut point) | **0.016158** |
| Arm 1 `σ_C` | **2.0** |
| Arm 3 `σ₃` | **4.0** |
| Arm 1 expected margin above `τ_hi` | **+0.0104** (Arm-1 calibration median HDG − `τ_hi`) |
| Arm 4 expected margin below `τ_lo` | **0.00091** (`τ_lo` − noise-null median HDG) |

These satisfy the §8 cut-point-validity setup control: `0 < τ_lo < τ_hi`, strict, with a band `[0.000852, 0.016158]` of width ≈ 0.0153 AUC. By the calibration percentile rules, ~95% of each null-like candidate's mass sits below `τ_lo` and ~95% of Arm 1's mass sits above `τ_hi` — consistent with the §7 ≥90/100 bars, though an **expectation, not a guarantee** (the positive control draws fresh data under its own seed `0xFACADE`, so a near-miss remains possible and would be reported as one). All symbolic references to `τ_lo`, `τ_hi`, `σ_C`, `σ₃` elsewhere in this document resolve to the values in this table.

---

## 6. Verdict rule (restated, deterministic)

For each (arm, replication): compute `D`; emit `Validated` if `D > τ_hi`, `Not-Validated` if `D < τ_lo`, `Inconclusive` if `τ_lo ≤ D ≤ τ_hi`. No power test, no confidence interval, no "is D clean enough" judgment (spec §3). Tally verdicts over the 100 replications per arm.

---

## 7. Per-arm pass thresholds (pre-committed, stratified)

| Arm | Property tested | Correct v0.1 verdict | Pre-committed bar |
|---|---|---|---|
| 1 — known-meaningful | sensitivity (Type-II floor) | Validated | **≥ 90 / 100** |
| 2 — deterministic-redundant | specificity vs redundant candidate | Not-Validated | **≥ 90 / 100** |
| 3 — partial-redundancy | sensitivity gradient + Inconclusive witness | (none) | **non-gated; report the full verdict distribution (V / NV / Inconclusive); band occupancy is the primary report** |
| 4 — pure-noise | false-discovery floor | Not-Validated | **≥ 90 / 100** |

Arm 3 is reported, not gated. Its **full verdict distribution** is reported — Validated, Not-Validated, and Inconclusive fractions — not just band occupancy, because the split is diagnostic of `σ₃` targeting (spec §4's "sensitivity gradient"): since smaller `σ₃` means a stronger (less-noised) increment, an Arm 3 landing mostly Validated means `σ₃` was set too **low** (too little noise → increment too strong), mostly Not-Validated means `σ₃` too **high** (too much noise → increment too weak), and a healthy Inconclusive mass means `σ₃` correctly targeted the band. Band occupancy is the primary number; the V and NV occupancies are reported alongside it. All three v0.1 verdicts are **exercised** by the study (Validated by Arm 1, Not-Validated by Arms 2/4, Inconclusive by Arm 3); the gated verdicts are additionally **certified** by their bars. A near-zero Inconclusive occupancy on Arm 3 is a recorded finding (band too narrow or `σ₃` mis-targeted), not a silent pass. Near-misses on gated bars are reported as near-misses.

---

## 8. Setup controls (failure invalidates the run; not a verdict)

Per spec §3, a setup-control failure invalidates the run rather than judging anything, and is documented + amended under a new tag, never silently re-run.

1. **Substrate non-degeneracy:** median `AUC_test(logistic[B])` across the 100 replications must exceed **0.60**. If the baseline itself carries no signal, HDG is measured against a degenerate baseline and the study is meaningless.
2. **Generator sanity / orientation:** (a) the calibration meaningful sweep showed HDG increasing with candidate signal strength (oriented higher-is-better) — **satisfied by the calibration result** (separability check 3, `USABLE BAND`), inherited here, not re-checked in this run; (b) the two null arms (Arm 2, Arm 4) must each have **mean HDG ≤ `τ_lo`** across the `R` replications — their centers sit below the not-validated floor; a null centering at or above `τ_lo` signals a generator fault. *(Part (b) operationalizes "centered at or below ~0" with a concrete threshold; pinned from the `validate_ovp.py` build — see `SCRIPT_BUILD_FINDINGS_POSCONTROL.md`.)*
3. **Cut-point validity:** the frozen cut points must satisfy `0 < τ_lo < τ_hi` (else §5's separability check failed and there is no study).

---

## 9. Baseline selection (§2 conformance) and Ancestry Statement

- **Same substrate:** `B` and every arm's `C` are derived from the same synthetic substrate (`s1, s2, y` draw).
- **Strictly simpler:** the baseline model uses `B` alone; the candidate model uses `B` **and** `C` (one additional feature). The candidate is strictly more complex by exactly the dimension under test; the baseline is never more complex than the candidate.
- **Pre-registered / no post-hoc:** `B`, the arm forms, the metric/estimator/split, and the cut-point procedure are committed at lock; none is swapped after results.
- **Ancestry Statement:** *"Candidate `C` extends baseline `B` on the same substrate: `C` is proposed to add out-of-sample discrimination of `y` beyond what `B` alone provides. `B` observes latent `s1`; the question is whether `C` contributes predictive structure (latent `s2`) that `B` cannot."*

---

## 10. Materialization, lock, and execution plan (ordered)

The calibration study is a **separate study** with its own pre-registration, its own cold pass, and its own lock. This positive-control pre-registration is **structurally incomplete** until the calibration outputs (`τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃`) are frozen into it — so its cold pass happens *after* that freeze, not before. The ordered sequence (each lock: single atomic commit + signed tag, AEPF discipline):

1. **Draft** the calibration pre-registration (`PRE_REGISTRATION_OVP_POSCONTROL_v1_CALIB.md`), with the same care as this document.
2. **Cold passes** on the calibration pre-registration (two independent, ≥1 cold; external; fix-author cannot clear).
3. **Calibration lock** (`ovp-poscontrol-v1-calib-lock`): calibration pre-reg + calibration script + materialization manifest. Then **run once** → produce `τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃`, and the §5 separability check.
4. **Freeze** those values into this positive-control pre-registration (the §4/§5 placeholders become numbers; the frozen values are recorded in §5.1).
5. **Cold passes** on this positive-control pre-registration (reviewable once the cut points are frozen, step 4): two independent external passes, ≥1 cold, fix-author cannot clear. The study does not lock (step 6) until both passes return no blocker.
6. **Positive-control lock** (`ovp-poscontrol-v1-lock`): this pre-reg (frozen), `validate_ovp.py`, materialization manifest. Then **run exactly once**.
7. **Write** `RESULT_OVP_POSCONTROL_v1.md` (PASS / FAIL / near-miss, published with parity regardless of outcome).
8. **Cross-pass** on the result (§7) before it may be cited as establishing the self-validated rung.

Single-execution applies to both runs: each runs once; a technical failure is documented and amended under a new tag, never silently re-run.

---

## 11. What this study does and does not establish

- **Does:** if it passes, OVP reaches the **self-validated** rung (spec §6, rung 1 — the rungs are unnumbered; this is the first) — the decision rule returns the known-correct verdict at the pre-committed rate on synthetic ground truth.
- **Does not:** make OVP operational or community-validated; validate any real candidate observable; or establish anything about OVP v0.2's redundant-vs-noise distinction (Arms 2 and 4 are deliberately undifferentiated here).
- Interpretation is constrained to the synthetic constructions and the pinned instantiation. A different metric, estimator, or substrate is a different question.

---

## 12. Cross-pass plan (§7)

Three cold-pass points, per the ordered sequence in §10: **(a)** the calibration pre-registration before its lock; **(b)** this positive-control pre-registration after the calibration values are frozen in (step 4) and before its lock (step 6); and **(c)** the result document before it may be cited (step 8). Each point requires **two independent verification passes**, at least one a cold reader with no design-conversation context; the fix-author (including the AI collaborator) cannot be a clearing reader; divergences are recorded.

---

## 13. Discretionary pins (pinned as written; for explicit pre-lock sign-off)

Every value in this document is **pinned as written**. This section gathers the *discretionary* ones — chosen by judgment rather than fixed by the spec or by construction — for explicit operator sign-off before lock. Confirming changes nothing in the text; amending one is an ordinary pre-lock edit. **This section is struck at lock.** (The cut-point–dependent items — `τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃` — are **not** open choices: they are *inherited* from the calibration study's locked outputs and frozen in at step 4 of §10.)

1. **Estimator:** L2 logistic regression, `C=1.0` — confirm (vs. a different regularization or a deliberately nonlinear estimator to make Arm 2's redundancy a stronger test).
2. **N = 4000, 50/50 split, R = 100 (fixed), R_cal = 200** — confirm sample sizes.
3. **Generative constants `β1 = 1.0`, `σ_B = 1.0`** — confirm (these set baseline strength; calibration confirms non-degeneracy).
4. **Cut-point rule (settled and executed in the calibration study — recorded, no longer open):** `τ_lo` = **max** of the two null types' 95th percentiles (not pooled); `τ_hi` = 5th pct of the weakest meaningful sweep point that clears `τ_lo + δ` (δ = 0.01 AUC). This rule was locked and run in the calibration study; the resulting **values are frozen** (§5.1), so this item needs no further sign-off.
5. **Setup-control threshold:** baseline median `AUC(B) > 0.60` — confirm the bar.
6. **Seeds:** calibration `0xCA11B`, positive control `0xFACADE` — confirm (any two distinct values are fine; pinning them here fixes them).

*End of draft pre-registration. Awaiting review; not locked.*
