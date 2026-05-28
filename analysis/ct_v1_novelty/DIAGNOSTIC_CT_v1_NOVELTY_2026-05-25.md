# Diagnostic: CT-v1 Novelty + Representation

**Status:** EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.

**Date:** 2026-05-27
**Operator:** Earl Dixon
**Protocol:** `CT_v1_NOVELTY_REPRESENTATION_DIAGNOSTIC_PROTOCOL.md`
**Formula lock:** `CT_v1_FORMULA_LOCK.md`

## Data summary
- Training subset (observed_at < 2026-05-15 UTC): 3,552 cells
- Comparison subset (observed_at >= 2026-05-15 UTC): 4,320 cells
- Cells excluded by 75% completeness rule: 48
- D1 paired cells (both predecessor CT and CT-v1 defined): 4,320

## D1 — Structural similarity (GATE)

**Pearson correlation (predecessor CT vs CT-v1):** 0.0491
**95% bootstrap CI:** [0.0172, 0.0844]
**Bootstrap:** B = 10,000, seed = 0x1DEA
**Spearman (secondary, reported for transparency):** 0.1410

### Verdict

**PROCEED**

Pearson correlation 0.0491 < 0.5 threshold. CT-v1's structural content is doing work distinct from predecessor formula. Advance to full AEPF cross-model review and lock as confirmatory study.

---

## Critical methodological caveat (added post-run, 2026-05-27)

**The PROCEED verdict above is the mechanical output of the locked decision rule. It is structurally misleading in this case, and that misleading character was surfaced by the diagnostic's own characterization layer (D3 in particular). This caveat is added without modifying the locked verdict to honor the protocol's discipline while documenting the substantive finding.**

### What the supporting diagnostics show

The D3 ablation correlations are extreme:

- Replacing E with its training-set median: r(no-E vs full CT-v1) = 0.9903
- Replacing M with its training-set median: r(no-M vs full CT-v1) = 0.9990
- Using uniform weights: r(uniform vs full CT-v1) = 0.9988

These mean the entropy term E and the phase-mix term M — the new structural content that distinguished CT-v1 from the predecessor formula — are contributing essentially zero to CT-v1's values. Additionally, the training-set medians of normalized E and M are both reported as 0.0000, confirming that these terms are near-zero across the training subset.

### Why this happens (verified post-run via `check_phase_degeneracy.py`)

A targeted verification check on the comparison-window atmospheric data confirmed:

- **88.5% of comparison-window cells have precipitation < 0.1 mm/h**, which sets the precipitation activity factor α = 0. In those cells, the formula lock's Section 3.5 forces `p_none = 1` and `p_rain = p_snow = p_ice = 0`, which forces E = 0, M = 0, and therefore CT-v1 = 0 by formula construction.
- In the 12.45% of cells with active precipitation, wet-bulb temperature ranged 8.60°C to 27.43°C. Zero cells fell in the freezing-rain transition band [0°C, 4°C]; zero cells were below freezing.
- The Koistinen-Saltikoff snow-probability sigmoid is essentially saturated at p_snow ≈ 0 across this entire temperature range. The ice-phase Gaussian centered at T_w = −1°C produces near-zero ice probability for all observed T_w. The phase distribution in active-precipitation cells collapses to {p_rain ≈ α, p_none = 1−α, p_snow ≈ 0, p_ice ≈ 0}.

### What the verdict actually means in this case

The PROCEED verdict reflects the fact that CT-v1 is forced to ≈ 0 in 88% of cells while predecessor CT (which does not depend on the precipitation activity factor) produces non-zero values in the same cells. The low Pearson correlation (r = 0.0491) is driven by this artifact of formula-data regime interaction, not by substantive structural novelty in CT-v1 relative to the predecessor formula.

CT-v1's novelty mechanism — the Shannon-entropy phase term E and the max-based phase-mix term M — is **structurally inert** in the available data regime. The dynametrix atmospheric observation history covers warm-season convective weather (April 20 – May 29, 2026), where phase variability is essentially zero by climate. The phase classifier framework as specified in the formula lock cannot meaningfully operate on this dataset regardless of classifier parameter choices.

### Methodological recommendation

Despite the PROCEED verdict per the locked decision rule, **CT-v1 as currently specified should NOT advance directly to a full AEPF lock as a confirmatory study against the available dynametrix dataset**. The eventual confirmatory audit would test a formula whose structural novelty mechanism cannot fire in the data, which would produce results that are not interpretable as evidence for or against the underlying coherence-tension hypothesis.

Three substantively distinct next-move options, with the choice belonging to the operator:

1. **Revise the formula (CT-v2).** Reformulate the phase entropy and phase mix terms to operate on quantities other than precipitation-phase probabilities in warm-season convective data. This is a meaningful formula change and requires a new lock document with a new diagnostic protocol. The Conditional Diagnostic Layer's first refinement cycle.

2. **Defer until cold-season data accumulates.** Wait until the dynametrix dataset extends through winter 2026-2027 (December onward), where phase variability exists by climate. Re-run the diagnostic against the cold-season comparison window. The CT-v1 lock remains valid; what changes is the diagnostic's data availability.

3. **Re-scope the coherence-tension framework.** Recognize that severe convective weather is dominated by updraft strength, shear, and instability rather than by precipitation-phase transitions. The phase-probability framing may be the wrong abstraction for this domain regardless of formula details. Archive CT-v1 as considered-but-deferred-due-to-domain-mismatch.

### How this diagnostic functions as methodology

The Conditional Diagnostic Layer worked as designed in this case. The D1 gate produced a mechanically PROCEED verdict on r = 0.0491, which alone would have advanced CT-v1 to a confirmatory lock under a misleading premise. The D3 characterization diagnostic surfaced that the novelty mechanism contributes ≈0 to CT-v1's values, and a targeted verification check confirmed the underlying cause. The combination — gate plus characterization plus operator-driven verification — is what distinguished a structurally substantive finding from the surface verdict.

This caveat section is appended to the diagnostic output without modifying the locked verdict, in keeping with the protocol's lock discipline. The verdict stands as PROCEED per the rule; the substantive interpretation, documented here, is that the verdict reflects formula-data regime mismatch rather than CT-v1's structural novelty doing operational work.

---

## D2 — Representation-equivalence stress test (characterization)

Per-perturbation median |Δ CT|:

| Perturbation | Δ CT-v1 | Δ CT-pred |
|---|---|---|
| P1_zscore | 0.0000 | 0.0000 |
| P2_phase_shift | 0.0410 | N/A |
| P3_4h_temp | 0.0000 | 0.0000 |
| P4_interpolate | 0.0000 | 0.0000 |
| P5_phase_encoding | 0.0000 | N/A |

**Rank correlation of perturbation sensitivities (Spearman):** 0.0000

## D3 — Entropy + mix ablation (characterization)

**Training-set median of normalized E:** 0.0000
**Training-set median of normalized M:** 0.0000

Correlation with full CT-v1 under each ablation variant:

| Variant | Correlation with full CT-v1 |
|---|---|
| CT-v1 without E (E → training median) | 0.9903 |
| CT-v1 without M (M → training median) | 0.9990 |
| CT-v1 with uniform weights | 0.9988 |

## D4 — Normalization control (characterization)

Correlation of CT-v1 with predecessor CT under each normalization scheme:

| Scheme | Pearson(CT-v1, CT-pred) |
|---|---|
| Min-max (locked) | 0.0491 |
| Z-score | 0.0563 |
| Quantile (5th/95th) | 0.0684 |

## D5 — Least-tuned region comparison (characterization)

**Least-tuned location (highest min observed_at):** `29172590-f05d-483c-b213-b851421e47ff`
**All locations pooled:** r = 0.0491 (n = 4,320)
**Least-tuned region only:** r = -0.0045 (n = 360)
**Complement (all other locations):** r = 0.0545 (n = 3,960)

## Interpretive choices made at implementation time

- 'wind' in formula lock Sections 5.1, 5.5, 5.6 interpreted as wind_speed_10m.
- 'humidity' interpreted as relative_humidity_2m.
- 'cloud_cover' computed via dewpoint depression proxy (formula lock Section 5.2).
- 'least-tuned region' selected by recency of first observation (protocol Section 10.2 tiebreaker).
- May 4-7 data-collection gap (task #92) handled by 75% completeness rule; affected cells excluded.

---

*EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. Cannot be cited as confirmatory
evidence in any subsequent published audit. If the finding turns out to be
substantively interesting in its own right, it must be re-derived under proper
AEPF lock discipline before publication.*
