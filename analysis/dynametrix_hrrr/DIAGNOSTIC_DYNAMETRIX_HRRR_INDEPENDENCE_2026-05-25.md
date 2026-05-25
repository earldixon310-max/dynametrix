# Diagnostic: Dynametrix v3 vs HRRR Residual Independence

**Status:** EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.

**Date:** 2026-05-25
**Operator:** Earl Dixon
**Protocol:** INDEPENDENCE_DIAGNOSTIC_PROTOCOL.md

## Data window
- Window: 2026-05-18 through 2026-05-24
- Matched location-hours: 2,016
- Verified events in matched set: 375

## Provisional HRRR-to-probability transformation
Updraft helicity (HRRR MXUPHL, 2-5 km AGL) track density above 25.0 m²/s² threshold, integrated over 40.0 km neighborhood radius, normalized to probability via SPC HREF-style reference curve.

## Primary metric

**Pearson correlation of residuals (Dynametrix v3 vs HRRR):** 0.9839
**95% bootstrap CI:** [0.9816, 0.9860]
**Bootstrap:** B = 1000, seed = 0x1DEA, stratified by event/non-event.

## Sanity checks (mean residuals; near zero = marginally well-calibrated)
- Mean Dynametrix residual: -0.1822
- Mean HRRR residual: +0.1836

## Per-category breakdown
- **tornado**: r = 0.9485, n = 1,710, events = 69
- **hail**: r = 0.9437, n = 1,706, events = 65
- **wind**: r = 0.9785, n = 1,882, events = 241

## Sample size and scope caveats

1. **Sample size constraint.** 8 days of continuous v3 data (May 18–25, 2026). The diagnostic window covers May 18–24 to avoid the partial-day output of May 25. Per-category event counts were anticipated to fall below the 30-event threshold; in practice, an active mid-May convective period combined with the 100 km verification radius and 24-hour valid window produced 375 verified events across the 2,016 location-hours, sufficient to populate all three event-category breakdowns. The headline correlation is driven by the full matched set; per-category correlations are reported for completeness.

2. **Marginal calibration mismatch.** Mean residuals indicate Dynametrix v3 systematically over-predicts (mean predicted probability ~37% vs. observed event rate ~18.6%) while the provisional HRRR-derived probability systematically under-predicts (mean ~0.6%). Pearson correlation is invariant to such marginal shifts, so the headline residual correlation captures signal-tracking agreement between the two predictors despite their disagreement on absolute probability calibration. The HRRR-to-probability transformation used here is provisional per the protocol; a locked study would select a separately-calibrated transformation, but the residual-correlation finding is robust to that choice because the correlation reflects fluctuation agreement, not level agreement.

3. **Single late-spring weather period.** The diagnostic data window represents a single eight-day slice in late May 2026. The residual correlation observed here may not represent the full June–October distribution that the prospective evaluation window would cover. This diagnostic verdict applies to the narrow procedural question of whether to proceed with the locked combination pre-registration, not to a broader independence claim across the full convective season.

## Decision per protocol §5

**Verdict:** DO_NOT_PROCEED

Residual correlation 0.984 > 0.7 threshold. Do not proceed with the full pre-registration. Document the diagnostic result, archive the draft pre-registration as a 'considered but deferred' artifact, and direct the next AEPF audit at a different target.

---

*EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. Cannot be cited as confirmatory
evidence in any subsequent published audit. If the finding turns out to be
substantively interesting in its own right, it must be re-derived under
proper AEPF lock discipline before publication.*
