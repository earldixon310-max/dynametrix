# Script-build findings — validate_ovp.py vs the positive-control pre-reg

Per the standing discipline (`OVP_DESIGN_HISTORY.md`, §7 interpretation + build-and-smoke precondition): the script is built strictly to the pre-reg; under-specified choices that affect results are returned to the pre-reg and pinned, not silently encoded. Build occurs **before** the positive-control pre-reg's two cold passes, so these pins are folded in first.

## Blocker-class (returned to the pre-reg before its cold passes)

**F1 — §8.2(b) null-centering threshold was unspecified.** The pre-reg said the null arms must be "centered at or below ~0" without an operational number; the script needs a concrete test. Pinned as: **each null arm (Arm 2, Arm 4) mean HDG ≤ `τ_lo`** across the `R` replications (centers below the not-validated floor; a null centering at or above `τ_lo` signals a generator fault). Folded into pre-reg §8.2(b). Script uses this.

## Non-blocker (implementation notes; consistent with the calibration script)

**F2 — Frozen cut points sourced by hardcode + cross-check.** `τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃` are hardcoded at full precision (from the locked `calibration_results.json`, tag `ovp-poscontrol-v1-calib-result`) and asserted equal to that file at startup (`crosscheck_calibration()`), so a transcription error cannot pass silently. The full-precision `τ_lo=0.0008520905552347899`, `τ_hi=0.016157622564950937` are used in the verdict rule (the pre-reg §5.1 table shows them rounded for readability).

**F3 — Baseline AUC for non-degeneracy captured once per replication.** `AUC(logistic[B])` is computed inside `hdg()` for every arm, but for the §8.1 non-degeneracy median it is captured from Arm 1 only (one value per replication). The baseline model does not depend on `C`, so any arm's baseline AUC is representative; capturing Arm 1's avoids double counting. Non-blocker.

**F4 — §8.2(a) inherited, not re-run.** The meaningful-sweep monotonicity (orientation) was verified in the calibration study (separability check 3, `USABLE BAND`). It is not re-checked in the positive-control run; the pre-reg §8.2(a) now states this explicitly. Non-blocker.

**F5 — Seeding / split / estimator identical to the calibration script.** Same `SeedSequence`-per-replication, shared substrate per replication with per-arm `C` drawn in fixed `ARMS` order, stratified 50/50 split with the split seed drawn from the replication rng, and the same pinned `LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True)`. Only the master seed (`0xFACADE`) and `R` (100) differ from the calibration. Non-blocker.

## Smoke validation (non-canonical seeds, numpy-only logistic)

Per the build-and-smoke precondition. The design was exercised against the **frozen** cut points (`τ_lo=0.000852`, `τ_hi=0.016158`) with a numpy IRLS logistic (not sklearn), reduced/real N, non-canonical seeds — validating direction and placement, not exact counts.

- **N=2000 (one seed):** Arm 1 = 89 Validated, Arm 2 = 100 NV, Arm 3 = 80 Inconclusive (clean band witness), Arm 4 = 84 NV; baseline AUC 0.651. Arm 1/Arm 4 dipped *below* the 90 bar — traced to the reduced N (wider HDG distributions → more band-spill), since the cut points were calibrated at N=4000.
- **N=4000 (three seeds, 0xBEEF / 0xC0DE / 0x1234):** Arm 1 Validated = {98, 91, 96}; Arm 4 NV = {96, 92, 95}; Arm 2 NV = 100 each; Arm 3 ~80% Inconclusive. **All gated bars (≥90) clear across all three seeds.**

**Read:** the design is sound and the arms place on the correct sides of the frozen band at the real N=4000; the N=2000 dip was a sampling-width artifact. Margins are **tight-but-adequate** (Arm 1 as low as 91 on one seed), consistent with the calibration's disclosed ~95% expected placement and the operator-accepted power risk (§13.4 lineage). The single locked run under sklearn + seed `0xFACADE` is expected to PASS; a near-miss remains possible and would be reported honestly per §1/§7 (no reseed), exactly as CALIB_POSCONTROL_v1's 89/100 was.

## Disposition

F1 folded into the pre-reg (§8.2b) before the cold passes — it is a pin a cold reader could legitimately have called. F2–F5 are documented implementation notes consistent with the locked calibration script. Smoke confirms design viability at N=4000; `validate_ovp.py` is ready for the positive-control pre-reg's two cold passes (its own authoritative `py_compile` + run happen on the operator's machine, since sklearn is not in the sandbox).
