# Cross-Pass Record — OVP_POSCONTROL_v1 Cut-Point Calibration Study

Per the calibration pre-reg §11 and the spec §7 two-pass discipline. Records both independent verification passes, any divergence, and how each reader's independence was sourced. The calibration study locks only when **two independent passes return no lock-blocker on byte-identical artifacts** (per `OVP_DESIGN_HISTORY.md`, §7 two-pass interpretation). Non-blocker findings are queued below and **not** folded before lock (folding would change the bytes and reset the pass count).

## Pass 1 — external cold reader

- **Date:** 2026-06-06
- **Independence:** external reader, no design-conversation context; given the calibration pre-reg + the locked spec body + the lock notice only. The fix-author (incl. the AI collaborator) did not serve as this pass.
- **Verdict:** **No conformance lock-blocker.** Design conforms to spec §1–§8 (cut-point provenance/bootstrap, strict `0 < τ_lo < τ_hi`, arm margins, setup-control failure handling, single-execution / atomic lock / cross-pass).
- **Status of bytes reviewed:** the current calibration pre-reg (post Arm-3 noise redesign and F1/F2 pins).

## Pass 2 — external cold reader

- **Date:** 2026-06-06
- **Independence:** second external reader, no design-conversation context; given the same three artifacts. Fix-author did not serve as this pass.
- **Bytes reviewed:** **byte-identical to Pass 1** — the pre-reg was not modified between the two passes (only this cross-pass record was written, which the readers were not given).
- **Verdict:** **No lock-blocker.** Confirmed conformance to spec §1–§8 (provenance/bootstrap, acyclicity, strict band, HDG orientation/single-measure, cross-pass, single-execution) and internal consistency (gated-arm arithmetic closes; the `P95`/`P5` interpolation pin is genuinely result-affecting at `R_cal=200` and correctly fixed).
- **Corroboration:** independently raised the **same** finding 1 (the §5 "scale-invariant" wording is exact only for unregularized logistic; conclusion holds) — classified non-blocker. No divergence between the two passes on the verdict.

## Two-pass result: CLEARED TO LOCK

Two independent passes returned **no lock-blocker on byte-identical artifacts** → the §7 / lock-bar requirement is met. Remaining before the atomic lock: operator sign-off on the §12 discretionary pins (chiefly finding 4, the Arm-1 power margin), then lock + single run on the authoritative machine.

## Non-blocker findings queue (fold in the FIRST post-lock revision cycle; do NOT fold before lock)

1. **§5 estimator justification is imprecise.** The text says the linear estimator "is scale-invariant ... absorbs the scale into the coefficient." With the pinned L2 penalty (`C=1.0`, features not standardized), the estimator is only *approximately* scale-invariant — the penalty couples to feature scale. The conclusion (sweep Arm 3 by noise, not scale; cut points measured empirically) still holds, and the smoke confirmed γ-scaling is effectively inert in practice, but the stated reason should be softened from "is scale-invariant" to "is approximately scale-invariant (the L2 penalty couples weakly to scale; empirically inert here)."
2. **§10 dangling cross-reference.** "the §6 maturity ladder" refers to the *spec's* §6; the calibration doc's own §6 is "Cut-point rules." Change to "the spec's §6 maturity ladder."
3. **§8 asymmetric margin reporting.** §8 records Arm 4's margin below `τ_lo` but not Arm 2's, though spec §4 gates both Arm 2 and Arm 4 at ≥90/100. Add Arm 2's margin (it is also placed below `τ_lo` by the max-of-nulls rule) for symmetry.
4. **§6 / §12.2 — Arm 1 power risk (operator sign-off, not a defect).** Pinning Arm 1 to the weakest-clearing meaningful point sets `τ_hi = P5` of Arm 1's own calibration distribution, so Arm 1 enters the positive control with ~95% expected mass above `τ_hi` against a ≥90/100 bar — a real sampling-power risk, disclosed honestly in §6 and routed to §12.2 for explicit operator sign-off. Spec §4 permits it (expected D clears the band, so the bar is testable). Operator should sign off consciously at lock.

## Procedural gates still open (per the study's own §9/§11/§12)

- Pass 2 not yet run/recorded.
- §12 discretionary pins await explicit operator sign-off (chiefly the §6 weakest-point `τ_hi` / Arm-1 margin in finding 4).

**Disposition:** **2 of 2 clean passes complete on byte-identical artifacts — cleared to lock.** Finding 1 corroborated by both passes (non-blocker, queued). Remaining: operator sign-off on §12 pins (chiefly finding 4), then lock + single run.
