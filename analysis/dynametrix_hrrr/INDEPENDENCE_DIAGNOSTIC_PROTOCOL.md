# Independence Diagnostic Protocol: Dynametrix v3 vs HRRR Residuals

**Status:** EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.

**Purpose:** Determine whether the residual errors of Dynametrix v3 and a provisional HRRR-derived probabilistic forecast are sufficiently independent to justify proceeding with the full Dynametrix-HRRR combination pre-registration (`PRE_REGISTRATION_DYNAMETRIX_HRRR_COMBO_v0.1_DRAFT.md`), or whether the independence assumption is structurally too weak for the combination study to be informative.

**Scope of this artifact:** This document specifies a methodological diagnostic to be run before deciding whether to lock the full Dynametrix-HRRR pre-registration. Its output is informational only. It cannot be cited as confirmatory evidence in any subsequent published audit. It does not lock anything.

---

## 1. Why this is exploratory rather than confirmatory

The independence diagnostic is not subject to AEPF lock discipline because (a) its purpose is to inform a methodological decision rather than to test a substantive hypothesis, (b) the HRRR-to-probability transformation used here is provisional rather than the production-locked transformation that would be used in the full study, and (c) the diagnostic's outcome does not constitute a finding about Dynametrix, HRRR, or any other system — it is a finding about whether a particular study design is structurally viable.

Treating this diagnostic as confirmatory and citing it later would be a methodological violation. The diagnostic should be documented in a brief markdown summary committed to the repository, but it should not be tagged, should not be packaged as a RESULT document, and should not appear in any AEPF case study without being re-derived under proper lock discipline.

## 2. Data scope

**Time window:** All days for which Dynametrix v3 has produced continuous outputs since the calibrator-v3.0 lock (task #61), excluding any days in the prospective evaluation window of the full study (June 1 – October 31, 2026). The diagnostic uses past data; the full study would use future data, with no overlap.

**Locations:** The current set of Dynametrix-monitored locations active under calibrator-v3.0.

**Forecast horizon:** 1-hour severe-weather probability, matching the full study's pre-registered horizon.

**Event categories:** Tornado, severe hail (≥ 1 inch), severe convective wind (≥ 58 mph), via the existing `storm_reports.py` ingestion.

**Minimum sample size for the diagnostic to be informative:** At least 200 location-hours containing matched Dynametrix and HRRR forecasts. If fewer matched location-hours are available, the diagnostic is reported as inconclusive and the decision on the full study is deferred until more data accumulates.

## 3. Provisional HRRR-to-probability transformation

For the diagnostic only, use updraft helicity (UH) track density above a 25 m²/s² threshold, integrated over a 40 km neighborhood radius around each location and the 1-hour forecast valid window, normalized to a probability via the operational reference curve (SPC HREF-style mapping).

This transformation is the operational community's default and is fit-for-purpose for the diagnostic. The locked production transformation for the full study can differ from this provisional choice — and ideally should be selected separately on its own merits, after the diagnostic determines whether to proceed.

If the UH archive is not readily accessible for the diagnostic window, a fallback is to use HRRR's own probabilistic guidance fields where available, or to use a thresholded composite (e.g., SCP > 4 as a binary fire signal, smoothed to a probability via a 40-km Gaussian). The fallback choice is documented in the diagnostic summary.

## 4. Method

**For each matched (location, forecast issue time):**
- Extract Dynametrix v3 calibrated probability: `p_dynametrix`
- Compute HRRR-derived probability via the provisional transformation: `p_hrrr`
- Determine the verified outcome from the SPC storm report match: `event` ∈ {0, 1}
- Compute residuals: `r_dynametrix = event - p_dynametrix`, `r_hrrr = event - p_hrrr`

**Aggregate metric:** Pearson correlation of `r_dynametrix` and `r_hrrr` across all matched location-hours.

**Bootstrap confidence interval:** B = 1,000 stratified resamples (stratified by event/non-event to maintain base rate), random seed `0x1DEA` recorded in the diagnostic script. Report Pearson correlation with 95% bootstrap CI.

**Secondary reporting (for context, not for decision):**
- Sample size (matched location-hours, of which N are verified events)
- Mean residual for each predictor (sanity check: should be near zero if both are well-calibrated; large nonzero means one or both is miscalibrated)
- Per-event-category breakdown of correlation (tornado, hail, wind) if sample sizes permit

## 5. Pre-committed decision rule on the diagnostic outcome

The decision on whether to proceed with the full Dynametrix-HRRR pre-registration is committed before the diagnostic is run, to prevent the diagnostic's outcome from being post-hoc reframed:

| Residual correlation (point estimate) | Decision |
|---|---|
| **< 0.4** | Proceed with the full pre-registration under normal AEPF discipline. Combination has structural room to add value. |
| **0.4 – 0.7** | Proceed with the full pre-registration, BUT add a required disclosure in §9 explicitly noting the bounded independence and the structurally-constrained upper bound on combination value. |
| **> 0.7** | Do not proceed with the full pre-registration. Document the diagnostic result, archive the draft pre-registration as a "considered but deferred" artifact, and direct the next AEPF audit at a different target. |

The threshold values are committed at this draft and are not adjusted after seeing the diagnostic result.

## 6. Diagnostic deliverable

A single markdown summary committed to the repository with:
- Diagnostic date and operator
- Data window and sample size (matched location-hours; verified events)
- Provisional HRRR-to-probability transformation used (specifically which one, and why if fallback)
- Pearson correlation with 95% bootstrap CI
- Per-event-category breakdown if available
- Decision per §5 (proceed unconstrained, proceed with disclosure, do not proceed)
- Explicit "EXPLORATORY DIAGNOSTIC, NOT A LOCKED RESULT" footer

File suggested name: `DIAGNOSTIC_DYNAMETRIX_HRRR_INDEPENDENCE_<date>.md`. Commit message should explicitly note "exploratory diagnostic; not a locked result."

## 7. What this diagnostic does NOT do

- It does not constitute a finding about Dynametrix's calibration or operational standing.
- It does not constitute a finding about HRRR's calibration or operational standing.
- It does not determine the combination's effectiveness; only whether the combination study is structurally viable.
- It does not lock any methodology; the full pre-registration's methodology decisions remain open and can be revised based on what the diagnostic reveals.
- It cannot be cited as confirmatory evidence in any subsequent published study. If the diagnostic's findings turn out to be substantively interesting in their own right (e.g., surprisingly high or low residual correlation), they must be re-derived under proper AEPF lock discipline before publication.

## 8. Estimated execution time

2–3 hours assuming: existing Dynametrix v3 output archive is queryable; HRRR archive is accessible for the diagnostic window via the standard NOAA archive; UH field extraction is straightforward. If the HRRR archive needs to be fetched and materialized for a long historical window, add 1–2 hours for data acquisition.

The diagnostic is intentionally lightweight. It is not a substitute for the full study; it is a gate on whether the full study is worth running.
