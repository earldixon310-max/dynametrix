# AEPF v1.1 — Discipline Refinements (working note)

**Status:** Working note, to be folded into the next revision of the framework specification and the methodology paper. These are refinements to the *practiced evaluation discipline* layered on top of AEPF; they do not alter the core Evidence Preservation Format (AEPF v0.1 — the cryptographic/procedural attestation substrate), which remains as specified.

**Date opened:** 2026-05-31
**Provenance:** All three lessons below surfaced during the RC_v1 → CALIB_POSCONTROL instrument-validation arc and are documented in the artifacts cited under each.

---

## Context: the Conditional Diagnostic Layer (already in use)

v1.1's headline addition, established before these lessons, is the **Conditional Diagnostic Layer** — a pre-specification viability gate that retires candidate studies whose informational yield is structurally over-determined before a confirmatory run is spent. Its first operational instance was the Dynametrix-HRRR independence diagnostic (r = 0.984, DO_NOT_PROCEED). The three lessons below are discipline refinements that accumulated alongside it.

---

## Lesson 1 — The numbers-reconciliation sweep

**Statement.** Before lock, extract every numerical constant that appears anywhere across the pre-registration and analysis code, and confirm they are mutually consistent. This is a verification surface distinct from coverage-checking (is every required section present?) and section-soundness (is each section internally correct?). Numbers that are individually plausible can still contradict each other across sections.

**Origin.** RC_v1. A first reconciliation sweep exposed an N_var / cell-size-floor contradiction (a variant count that, combined with a per-cell minimum, implied zero evaluable cells); a second pass exposed a variant-capacity shortfall in the non-framing bins that collapsed the multi-bin design to a single bin. Neither was visible from reading any single section. Documented in `analysis/relational_coherence_v1/NUMBERS_RECONCILIATION_RC_v1.md`.

**Operationalize.** Add an explicit numbers-reconciliation pass to the pre-lock checklist, owned separately from coverage and soundness review, producing a constants ledger that is confirmed before the lock commit.

---

## Lesson 2 — Reviewer-context saturation and the cold-reader role

**Statement.** In an extended collaborative design conversation, every participant — every model instance and the operator — accumulates context saturation: shared assumptions become invisible, and a contradiction introduced mid-design can survive multiple reviews because every reviewer was present when the change was rationalized. Cross-model review therefore provides genuine independence **only if at least one reviewer is cold to the design conversation** — given the artifacts and the standards, but not the history.

**Origin.** RC_v1. The §10 five-line lock summary disagreed with the body after a template count changed (12/60/select-50 → 10/50/all-50); two warm reviewers (the workspace reviewer and the operating model) missed it; a cold reviewer caught it on first read. That contradiction was a self-inconsistent core lock that would have invalidated the study.

**Operationalize.** For any study reaching lock, require at least one review pass from a reviewer cold to the design conversation, reading the on-disk artifacts directly rather than the design narrative. Treat warm review as drift-catching, not as the independence gate.

---

## Lesson 3 — Stratified pre-committed criteria for instrument-validation studies

**Statement.** When the object under test is an evaluation *instrument* (validated against synthetic ground truth) rather than a hypothesis about the world, the pre-committed success criteria must be **stratified by the property under characterization** — soundness, power, robustness under specific named challenges — rather than collapsed into a single conjunction across heterogeneous arms. A single bar spanning arms that probe different properties will fail for reasons that do not bear on the property that matters, obscuring rather than revealing the instrument's operating characteristics.

**Origin.** CALIB_POSCONTROL. A single pre-committed bar — "every positive-control arm classified Calibrated in ≥ 90/100" — merged *soundness* (zero false-accept of broken calibration; near-zero false-reject under well-spread conditions) and *power under skew* into one conjunction. The soundness property held completely (zero false-accept across four miscalibration families; 100% acceptance of well-spread calibrated data), but a skewed-but-calibrated arm scored 89/100 on a pure statistical-power artifact — reduced bin-wise power under concentrated predictions, the limitation §7.2 of the audit template had named a priori. The single-conjunction bar reported this as an overall FAIL, conflating a power characteristic with a soundness failure. Documented in `analysis/calib_instrument_validation/INSTRUMENT_VALIDATION_NOTE.md`.

**Operationalize.** Instrument-validation pre-registrations specify criteria of the form: *soundness* arms (binding, e.g. zero false-accept across negative controls); *power-baseline* arms (binding, e.g. ≥ X/N under well-spread conditions); and *power-under-named-difficulty* arms (reported as characterization, not gated, where a documented reason predicts reduced power). Each arm is mapped to the property it probes before execution.

**Guardrail (carried from the CALIB_POSCONTROL note).** The disciplined report of a near-miss FAIL can strengthen a finding's credibility — but this is a contained claim, earned case-by-case by a small failure, a sharp diagnosis, and an interpretation constrained by an a-priori commitment. It is not a general principle that FAIL outranks PASS. If reports routinely relied on a substantive-interpretation move to recover from failed bars, pre-committed bars would become decoration — the inversion the framework exists to prevent.

---

## A note on referents (cross-cutting)

Two v1.1 cases — CT-v1 and CALIB_POSCONTROL — both exhibit the pattern "mechanical verdict preserved, substantive interpretation documented, both reported," but they characterize different referents and the distinction should be kept explicit in any writeup. CT-v1's mechanical-PROCEED-with-caveat concerned **substrate degeneracy** (a finding about the world the instrument was applied to: the phase classifier was inert in 88.5% of cells). CALIB_POSCONTROL's mechanical-FAIL-with-interpretation concerned an **instrument power limitation** (a finding about the tool itself). Same discipline; different referent (world vs instrument). The discipline is the constant; what is being characterized is not.

---

*Working note. Fold into the framework specification revision and the methodology paper's discussion of operating discipline.*
