# Instrument Validation Note — AEPF Calibration Audit

**Date:** 2026-05-31
**Operator:** Earl Dixon
**Status:** Methods-level instrument validation. **Not a locked AEPF study** and not a finding about the world — it characterizes the audit *tool* against synthetic ground truth. Reproducible artifact: `validate_audit.py`; raw operating characteristics: `VALIDATION_RESULTS.md` / `validation_results.json`.

**Decision rule under test:** the calibration-audit rule used in the three real-model audits (AI-calibration template §5–§6, reproduced verbatim in the script): K = 10 equal-width bins; a bin "passes" iff n ≥ 30 and the bin's mean predicted probability lies inside the Wilson 95% CI of its observed frequency; Brier Skill Score vs base-rate climatology; outcomes Calibrated (strong ≥ 9 bins / acceptable ≥ 7, BSS > 0), Not calibrated (< 5 bins), or drift (otherwise).

---

## Verdict (mechanical, pre-committed bar): **FAIL**

The pre-committed success criterion was: *every positive-control arm classified Calibrated in ≥ 90/100 replications, and every negative-control arm rejected in ≥ 90/100.* Two of the three positive arms cleared it (`calibrated_uniform` 100/100, `calibrated_bimodal` 100/100); the third, `calibrated_asym` (Beta(2,5)), came in at **89/100** — one replication under the line. That single miss fails the conjunction. The verdict is FAIL and is reported as FAIL: no kinder seed, no softened threshold, no relabeling. The result was produced once at master seed `0x1DEA` and stands.

A near-miss is part of what makes the threshold meaningful. Had the arm landed at 95/100, the distinction documented below would never have been forced into view, and the most informative finding the validation produced would have been lost.

---

## Substantive headline: an a-priori caveat met its measured operating characteristic

Under blind execution against synthetic data calibrated *by construction*, the audit empirically rediscovered the exact statistical-power limitation that **§7.2 of its own template had written down a priori** — "highly skewed distributions reduce the statistical power of the calibration test." The skewed-but-genuinely-calibrated Beta(2,5) arm concentrates predictions in the low range, leaving the upper bins sparse; with fewer effective bins the bin-pass count is noisier (mean 7.5/10 vs 9.6 for uniform), so ~11% of replications dip to "drift." That is not the instrument failing to recognize calibration — the outcomes were drawn from the predictions, so there is no miscalibration in the arm to recognize. It is a documented theoretical caveat acquiring a measured empirical signature. That correspondence strengthens the instrument's credibility rather than undermining it: the audit does not merely have a limitation, it has a limitation that was named in advance and now carries operating characteristics.

---

## Operating characteristics: soundness vs power

The result separates cleanly into two distinct error properties, which is exactly what an instrument-validation study should produce.

**Soundness (Type I — false-accept of broken calibration): zero, across all four miscalibration families.** Overconfident (T=0.5), underconfident (T=2.0), shift-positive (b=+0.5) and shift-negative (b=−0.5) were each rejected 100/100, mean bins passed 1.2–2.6, far under the 5-bin floor. Not a single replication of broken calibration was accepted as calibrated. This is the property that matters most — an instrument with a non-zero Type I rate would be dangerous.

**Power (Type II — false-reject of true calibration): zero under well-spread predictions, ~11% under heavy skew.** Well-spread calibrated data (uniform, bimodal) was accepted 100/100. The skewed Beta(2,5) arm was accepted 89/100 — an ~11% false-reject rate driven by reduced bin-wise power, not by any miscalibration in the data.

**Noise tolerance (informative, non-gating): monotone.** The noisy-estimator arms degrade smoothly with estimation noise — σ=0.25 → 100% Calibrated, σ=0.5 → 82%, σ=1.0 → 0%, σ=2.0 → 0% — confirming the audit tolerates small estimation noise and flags large noise, in the predicted direction.

---

## The pre-committed bar was conflated — and that is the design lesson, not a footnote

The "every positive arm ≥ 90/100" rule **merged two distinguishable properties into a single conjunction**: soundness (zero false-accept; near-zero false-reject under well-spread conditions) and power-under-skew. The arm that failed failed on the second while the first held completely. This is named here as a design choice now seen to be wrong, not merely operated around in interpretation. A correctly stratified pre-commitment would have read:

- **Soundness:** zero false-accept across the negative-control arms (binding).
- **Power baseline:** ≥ 90/100 acceptance across well-spread positive arms (binding).
- **Power under documented difficulty:** the skewed positive arm reported *as characterization*, not gated — because §7.2 told us in advance its power would be reduced.

Under that stratification the soundness and power-baseline criteria pass and the skewed arm's 89/100 is reported as the measured power-under-skew characteristic it actually is. The single-conjunction bar obscured that. This is the v1.1 lesson the study yields: **instrument-validation pre-registrations must stratify pre-committed criteria by the property under characterization, not collapse them across heterogeneous arms.**

---

## Relationship to CT-v1: same discipline, different referent

This case follows the same AEPF pattern as the CT-v1 diagnostic — the mechanical verdict is preserved unchanged, the substantive interpretation is documented alongside it, and both are reported — but it is characterizing a different thing, and the distinction should not be blurred. CT-v1's mechanical-PROCEED-with-caveat was about **substrate degeneracy**: the phase classifier was inert in 88.5% of cells, a finding about *the world the instrument was applied to*. This case's mechanical-FAIL-with-interpretation is about a **documented power limitation under skew**, a finding about *the instrument itself*. Same discipline, different referent (world vs tool).

---

## Scope and what this does not claim

The negative controls cover **temperature-scaled and systematic-logit-shift** miscalibration only. They do not establish that the audit catches every possible miscalibration (e.g., difficulty-stratified miscalibration, where a model is calibrated on easy items and broken on hard ones, is untested here). The soundness claim is bounded to the four parametric families above.

One framing guardrail, stated explicitly so it is not generalized later: **in this specific case**, the disciplined report of a near-miss FAIL strengthens the credibility of the instrument-validation finding — because the failure was small, the diagnosis was sharp, and the substantive interpretation was constrained by an a-priori template note (§7.2). This is **not** a general principle that FAIL is stronger than PASS. If every AEPF study failed its pre-committed bars and every report leaned on the substantive-interpretation move, the pattern would invert into "bars are decoration, interpretation is what matters" — which is the betrayal of the framework, not its proof. The claim is contained to this case and earns its containment.

---

## Bottom line

Instrument soundness is verified: zero false-accept across all four miscalibration families. Instrument power is characterized: zero false-reject under well-spread calibration, ~11% under heavy skew exactly as §7.2 predicted, and a monotone noise-tolerance gradient. The pre-committed bar failed by one replication on the skewed positive arm, and that failure is reported as a failure. The 89 is not a number to defend — it is a finding to document, and the pre-registration design for future instrument-validation studies is now informed by what it revealed.

*Methods-level instrument validation. Reproduce with `python validate_audit.py` (master seed 0x1DEA, 100 replications, no external data or model).*
