# RESULT — OVP_POSCONTROL_v1 (positive control)

## Verdict: **PASS** — OVP reaches the **self-validated** rung (spec §6, rung 1)

**Study:** OVP_POSCONTROL_v1, the positive control for the Observable Validation Protocol.
**Governing spec:** OVP v0.1 @ signed tag `ovp-v0.1-lock` (conforms without modification).
**Locked at:** signed tag `ovp-poscontrol-v1-lock` (pre-reg + `validate_ovp.py` + manifest; two independent cold passes on byte-identical artifacts, no lock-blocker; operator signed off §13).
**Executed:** **once**, under master seed `0xFACADE`, scikit-learn 1.8.0 / numpy 2.1.2 / Python 3.12.10 (per `materialization_manifest_poscontrol.json`). Output: `poscontrol_results.json`.
**Cut points (frozen, inherited from `ovp-poscontrol-v1-calib-result`):** `τ_lo = 0.000852`, `τ_hi = 0.016158`; Arm 1 `σ_C = 2.0`, Arm 3 `σ₃ = 4.0`. Verified at runtime against `calibration_results.json`.

---

## Per-arm verdicts (R = 100 replications each)

| Arm | Construction | Correct verdict | Validated | Not-Validated | Inconclusive | Bar (≥90/100) | Result |
|---|---|---|---|---|---|---|---|
| **1 — Known-meaningful** | `C = s2 + N(0, 2.0²)` | Validated | **95** | 0 | 5 | ≥90 Validated | **PASS** |
| **2 — Deterministic-redundant** | `C = 2B − 0.5` | Not-Validated | 0 | **100** | 0 | ≥90 Not-Validated | **PASS** |
| **3 — Partial-redundancy** | `C = B + s2 + N(0, 4.0²)` | (band witness) | 4 | 5 | **91** | non-gated | reported |
| **4 — Pure-noise** | `C = N(0,1)` | Not-Validated | 0 | **93** | 7 | ≥90 Not-Validated | **PASS** |

All three **gated** bars met. **Arm 3** exercises the Inconclusive verdict under its intended condition — 91/100 land in the band — so all three v0.1 verdicts (Validated, Not-Validated, Inconclusive) are demonstrated by the control, none shipping uncertified.

## Setup controls (all hold — the run is valid)

1. **Substrate non-degeneracy:** median baseline `AUC(B) > 0.60` — **true**.
2. **Null-centering:** mean HDG of Arm 2 and Arm 4 each `≤ τ_lo` — **true**.
3. **Cut-point validity:** `0 < τ_lo < τ_hi` — **true**.

## Margins / honesty note

The result is a clean PASS, not a near-miss: Arm 1 at 95/100 and Arm 4 at 93/100 sit comfortably above the 90 bar (the calibration placed each arm at ~95% expected, and this single fresh-seed draw realized within that expectation). Per AEPF single-execution discipline, this is the one and only run — no reseed, no softened threshold. Had any gated arm landed at 88–89, it would have been reported here as a near-miss with the soundness-vs-power distinction documented (as the calibration audit's 89/100 was); it did not.

---

## What this establishes — and what it does not

- **Establishes:** OVP's decision rule (HDG against two pinned cut points → one of three verdicts) returns the **known-correct** verdict at the pre-committed rate on synthetic ground truth. By spec §6, OVP is now **self-validated** (rung 1).
- **Does not establish:** that OVP is **operational** (needs ≥3 real candidate-observable verdicts in the ledger) or **community-validated** (needs ≥1 externally-authored candidate). It validates no real candidate observable, and says nothing about OVP v0.2's redundant-vs-noise distinction (Arms 2 and 4 are deliberately undifferentiated in v0.1).
- **Interpretation is constrained** to the synthetic constructions and the pinned instantiation (AUC, L2 logistic, 50/50 split, the frozen cut points). A different metric, estimator, or substrate is a different question.

## Citation gate (spec §7, §10 step 8)

This result **may not yet be cited** as establishing the self-validated rung. Per the spec, the result document earns **two independent verification passes** (≥1 cold reader, no design-conversation context; the fix-author cannot clear) before it is citable. Until those clear, the PASS is recorded but not yet established. Status is tracked in `CROSSPASS_OVP_POSCONTROL_v1.md`.

## Queued for v0.x (non-blocker, from the pre-reg cold passes)

- §11 wording: "the rungs are unnumbered" — spec §6 in fact numbers them (1/2/3). Cosmetic; substance ("self-validated is the first rung") correct. Fold at the next revision.

*End of RESULT_OVP_POSCONTROL_v1.*
