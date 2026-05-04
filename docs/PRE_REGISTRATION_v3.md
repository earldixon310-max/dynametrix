# Dynametrix Verification Pre-Registration — v3 (DESIGN)

**Version:** v3.0
**Model identifier:** `calibrator-v3.0`
**Status:** **DESIGN LOCKED, IMPLEMENTATION PENDING.** This document specifies what v3 will be before it is built. Implementation must faithfully execute the spec below; no parameter, weight, or transformation may differ from this document at the time the v3 pipeline writes its first prediction. The implementation step will produce a separate pre-registration that confirms the spec was implemented as locked here, with the corresponding code commit hash recorded.
**Author:** Earl Dixon
**Lock date (design):** 2026-05-04
**Supersedes verification of:** none. v3 generates its own verification record. v1 and v2 reliability data remain historical and are not retroactively reinterpreted. v2 is preserved as a comparison baseline (Section 5).

---

## Scientific Question

> **Given richer but still imperfect atmospheric inputs, does the CI/CSO transformation produce a signal that outperforms standard baselines — specifically and most importantly, an atmospheric logistic regression on the same inputs?**

This question defines the falsifiable claim of v3. Every methodological choice in this document serves to answer it honestly. The atmospheric logistic comparison is the critical baseline because beating it is what distinguishes the framework's structural intelligence layer from a simple weighted combination of the same atmospheric variables.

---

## 1. Purpose and Hypothesis

This document fixes the design of v3 in advance of implementation and testing. v3 has a single, specific scientific purpose: **to test whether the lack of skill demonstrated by v2 is attributable to insufficient input variables, rather than to a fundamental failure of the CI/CSO/MCC framework.**

**Hypothesis under test:**

> The v2 framework's failure to show skill against severe-weather outcomes is caused by feeding it only three primitive weather variables (precipitation, surface pressure, temperature). When the same framework architecture is fed atmospheric variables operationally validated for severe-weather forecasting (CAPE, dewpoint depression, wind shear, pressure tendency), it will produce calibrated commitment_probability that demonstrates Brier skill score positive against climatology, persistence, SPC outlook, and an atmospheric logistic baseline.

**Possible outcomes of v3:**

- **v3 shows skill against all four baselines.** Hypothesis supported. The framework's structural intelligence layer adds value when fed appropriate atmospheric inputs. The CI/CSO/MCC research program is empirically backed.
- **v3 shows skill against climatology and persistence but not against an atmospheric logistic baseline.** Mixed result. The framework reproduces what's already in the inputs but does not add value beyond what simpler models extract. Whether this constitutes a useful contribution depends on operational considerations beyond pre-registration scope.
- **v3 shows no skill against climatology.** Hypothesis falsified. The insufficient-inputs explanation does not hold. v2's failure is more likely due to the framework's architecture, weighting, threshold structure, or core conceptual approach. v4 (if pursued) would need to address one of those root causes rather than expanding inputs further.

This document does not claim v3 will succeed. It registers the methodology by which the question will be answered.

---

## 2. Primary Verification Metric

**`commitment_probability`** — the scalar output produced by the v3 implementation of `run_pipeline` in `backend/app/services/engine_service.py` for a given location at a given time.

Dimensionally identical to v1 and v2's `commitment_probability`. The formula that produces it is unchanged (Section 7.5). What differs is exclusively the input data and the feature builder's transformation chain (Section 7).

---

## 3. Verification Windows

**Primary window:** 0–48 hours after the prediction's `observed_at` timestamp.
**Secondary window (also registered):** 0–24 hours after the prediction's `observed_at` timestamp.

Identical to v1 and v2.

---

## 4. Event Label

A binary outcome per prediction-window pair:

```
y = 1 if at least one SPC storm report (event_type ∈ {tornado, hail, wind})
        occurred within 50 km of the prediction location and within the
        verification window;
    0 otherwise.
```

Identical to v1 and v2.

---

## 5. Baselines

The five baselines from v2 are preserved exactly:

1. **Climatology** — constant forecast equal to historical base rate.
2. **Persistence** — today equals yesterday's `commitment_probability`.
3. **SPC Convective Outlook** — SPC's day-1 outlook category mapped to a probability.
4. **Atmospheric logistic baseline** — logistic regression on raw atmospheric inputs (CAPE, dewpoint depression, wind shear proxy, pressure tendency) trained on data prior to the v3 evaluation period.
5. **v2 baseline** — the v2 verification record from `calibrator-v2.0` over the same time window.

**Additional v3-specific baseline:**

6. **v1 baseline** — the v1 verification record from `calibrator-v1.0` over the same time window. v3 should also outperform v1, which used a static historical CSV.

A claim of "v3 has skill" requires:

- Positive Brier skill score against Baselines 1, 2, and 3.
- **Critically: positive Brier skill score against Baseline 4 (atmospheric logistic).** Without this, v3's structural intelligence layer is not adding value beyond what the inputs themselves provide via a simpler model. This is the meaningful test of the framework's value-add as a research contribution.
- Demonstrably better calibration than Baselines 5 and 6 (v2 and v1).

---

## 6. Reported Statistics

For each baseline comparison: POD, FAR, CSI (with Wilson 95% CI at decision threshold 0.5), Brier score, Brier skill score, reliability diagram with 10 bins, sample size per bin and confidence intervals.

Statistics with sample size below 100 per location-window are marked "preliminary" and not used for skill claims.

Identical to v1 and v2.

---

## 7. Feature and Pipeline Specification — `calibrator-v3.0`

This section defines the v3 implementation. The implementation step must faithfully execute this spec; deviations require a new pre-registration.

### 7.1 Input data flow

Per pipeline call (location L, time T):

1. Query `atmospheric_observations` for `location_id = L` and `observed_at ∈ [T - 96h, T]`, with `observed_at <= now_utc` (or `<= target_time` for backfill).
2. Sort ascending by `observed_at`.
3. Require at least 8 observations; if fewer, return no output and write no CalibratedOutput row.

Identical to v2.

### 7.2 Input variable mapping (CHANGED)

The v3 feature builder consumes the following atmospheric variables from `atmospheric_observations`:

| Variable | Column in atmospheric_observations | Notes |
|---|---|---|
| `cape` | `cape` | J/kg, Open-Meteo gfs_seamless |
| `temperature_2m` | `temperature_2m` | °C |
| `dewpoint_2m` | `dewpoint_2m` | °C |
| `pressure_msl` | `pressure_msl` | hPa, sea-level adjusted |
| `wind_speed_10m` | `wind_speed_10m` | m/s |
| `wind_speed_80m` | `wind_speed_80m` | m/s |
| `wind_speed_180m` | `wind_speed_180m` | m/s |
| `precipitation` | `precipitation` | mm in past hour, **retained** for storm_intensity_score |

Variables explicitly **not used** in v3 (not available from the chosen data source):

- True 0-6 km bulk wind shear (we use a proxy from 10/80/180m winds; documented limitation)
- 0-1 km storm-relative helicity (not available without a storm-motion estimate; documented limitation)
- Mid-level lapse rates (700/500 hPa pressure-level temperatures not reliably available; documented limitation)

A future v4 could integrate these by switching to a different data source (NOMADS HRRR via GRIB2 parsing, or a research data contract).

### 7.3 Derived atmospheric quantities (NEW in v3)

Computed from the input variables above before the structural feature stage:

```
dewpoint_depression = temperature_2m - dewpoint_2m            (°C)
shear_proxy_60m     = | wind_speed_80m - wind_speed_10m |     (m/s)
shear_proxy_180m    = | wind_speed_180m - wind_speed_10m |    (m/s)
pressure_drop_3h    = -1 × pressure_msl.diff(3)               (hPa)  [v2 compatible]
cape_change_3h      =  cape.diff(3)                           (J/kg)
dewpoint_depression_change_3h = dewpoint_depression.diff(3)   (°C)
precip_3h           = precipitation.rolling(3, min=1).mean()  (mm)
```

All differences are filled to 0 on missing values.

### 7.4 v3 Feature Builder Transformation Chain

The v3 feature builder maps atmospheric inputs to the seven structural features that `commitment_probability` consumes. Each structural feature has a documented v3 derivation:

**`storm_intensity_score`** — magnitude of present convective fuel:

```
cape_normalized = clip(cape / 2500, 0, 1)
precip_normalized = clip(precip_3h / 5, 0, 1)
storm_intensity_score = clip(0.65 * cape_normalized + 0.35 * precip_normalized, 0, 1)
```

CAPE 2500 J/kg is the "strongly unstable" reference. 5 mm/hr precip is the "moderate convective rainfall" reference.

**`storm_transition_score`** — atmospheric organizing toward storm-capable state:

```
shear_normalized = clip(shear_proxy_180m / 15, 0, 1)
pressure_drop_normalized = clip(|pressure_drop_3h| / 5, 0, 1)
storm_transition_score = clip(0.50 * shear_normalized + 0.50 * pressure_drop_normalized, 0, 1)
```

15 m/s as the reference for "significant" shear at the 180m level. 5 hPa/3hr pressure drop as the reference for "active synoptic forcing."

**`phase_transition_score`** — rate at which atmospheric state is reorganizing:

```
cape_rise = clip(max(0, cape_change_3h) / 1000, 0, 1)
moisture_increase = clip(max(0, -dewpoint_depression_change_3h) / 5, 0, 1)
pressure_rate = clip(|pressure_drop_3h - pressure_drop_3h.shift(3)| / 3, 0, 1)
phase_transition_score = clip(
    0.40 * cape_rise +
    0.35 * moisture_increase +
    0.25 * pressure_rate,
    0, 1
)
```

CAPE rising by 1000 J/kg in 3h indicates strong destabilization. Dewpoint depression closing by 5°C in 3h indicates rapid moistening. Pressure tendency derivative captures synoptic acceleration.

**`phase_prob_entropy`** — uncertainty / mixedness of atmospheric state:

```
window = 6  # hours
cape_var = cape.rolling(window, min=2).std() / 500
ddep_var = dewpoint_depression.rolling(window, min=2).std() / 5
press_var = pressure_msl.rolling(window, min=2).std() / 5
phase_prob_entropy = clip(0.40 * cape_var + 0.35 * ddep_var + 0.25 * press_var, 0, 1)
```

Higher recent variance across atmospheric variables → higher entropy → less resolved phase.

**`ci_confidence`** — quality and stability of the atmospheric signal:

```
ci_confidence = 1 - phase_prob_entropy
```

Inverse relationship: when atmospheric state is well-resolved (low entropy), CI confidence is high. When state is mixed and noisy, CI is low.

**`stability`** — how persistent the current atmospheric state is:

```
stability = clip(
    1 / (1 + |cape_change_3h| / 500 + |pressure_drop_3h| / 3),
    0, 1
)
```

Lower rates of change → higher stability. CAPE and pressure both contribute, weighted by their characteristic scales.

**`reliability`** — autocorrelation of atmospheric state over recent window:

```
window = 6
cape_lag1_corr = cape.rolling(window, min=3).apply(lag1_autocorrelation)
pressure_lag1_corr = pressure_msl.rolling(window, min=3).apply(lag1_autocorrelation)
reliability = clip(
    0.5 + 0.5 * (0.6 * cape_lag1_corr + 0.4 * pressure_lag1_corr),
    0, 1
)
```

`lag1_autocorrelation` returns Pearson correlation of x[1:] vs x[:-1] over the window, in [-1, 1]; rescaled to [0, 1].

### 7.5 Commitment formula — UNCHANGED FROM V1 AND V2

After the v3 feature builder runs, the pipeline takes the **last row** (most recent observation) and applies the unchanged commitment formula:

```
organization = 0.35 * phase_transition_score
             + 0.25 * storm_transition_score
             + 0.20 * storm_intensity_score
             + 0.10 * phase_prob_entropy
             + 0.10 * ci_confidence

commitment_probability = clip(0.18 + 0.70 * organization, 0.05, 0.95)

confidence = clip(
    0.25 + 0.35 * ci_confidence + 0.20 * reliability + 0.20 * stability,
    0.05, 0.95
)
```

**Critical methodological note:** The weights in the commitment formula are deliberately preserved from v1/v2. v3 changes one thing — the inputs that feed the structural features — and tests whether that change alone produces calibrated outputs. Re-fitting these weights against v2 verification data is explicitly prohibited (it would constitute overfitting). If v3 fails and a future v4 is justified, weight re-derivation would itself require a separate pre-registration documenting the derivation methodology.

### 7.6 Lifecycle classification — UNCHANGED FROM V1 AND V2

```
if commitment_probability ≥ 0.68:    lifecycle = commitment;       lead = 6h
elif commitment_probability ≥ 0.50:  lifecycle = pre_commitment;   lead = 12h
elif phase_transition_score > 0.65 and storm_transition_score > 0.25:
                                     lifecycle = reconfiguration;  lead = null
elif commitment_probability < 0.30:  lifecycle = decay;            lead = null
else:                                lifecycle = quiet;            lead = null
```

### 7.7 CT (diagnostic, not part of verification target) — UNCHANGED

```
instability = 0.50*phase_transition_score + 0.30*storm_transition_score + 0.20*storm_intensity_score
competition = 0.70*phase_prob_entropy + 0.30*phase_mix_score_3h
persistence = clip(0.45*stability + 0.35*reliability + 0.20*ci_confidence, 0.05, ∞)
CT = (instability * competition) / sqrt(persistence + 1e-8)
```

Note: `phase_mix_score_3h` from v2 is preserved as-is for compatibility with the CT formula. v3's computation of phase_mix is left unchanged (precip flag + temp flip), as the CT diagnostic is not part of the v3 hypothesis under test.

---

## 8. Decision Threshold

**0.5** (unchanged). Outcomes also stored at thresholds 0.3 and 0.7 for parallel evaluation; 0.5 is the registered headline.

---

## 9. Sample Size and Reporting Cadence

Statistics computed and published quarterly, beginning the calendar quarter following 100 verified predictions per location. Below 100 marked "preliminary," no skill claims.

---

## 10. Held-Out Test Period

**Critical for v3:** The v3 verification record begins accumulating only from predictions made at or after the v3 implementation lock date. **Predictions made during the v2 evaluation window must not be used to assess v3 skill**, because the v2 verification record informed the design of v3 (specifically, the choice to add atmospheric variables), making that period informationally contaminated.

The v3 verification record is therefore a fresh accumulation. Initial skill claims wait until 100+ verified v3 predictions per location have closed windows — likely 2-4 weeks under the hourly schedule.

If historical backfill is performed for v3 (analogous to the v2 backfill done on 2026-05-03), it must use atmospheric data from a period **other than** the v2 evaluation window (April 27 – May 4, 2026), to maintain held-out integrity.

---

## 11. Known Limitations of v3

**Limited shear/helicity proxies.** True 0-6 km bulk shear, 0-1 km SRH, and storm motion are not available from Open-Meteo `gfs_seamless`. v3 uses a 10m-180m wind speed difference as a shear proxy. This captures only a fraction of what operational severe-weather composites use. A v4 with HRRR-direct GRIB2 ingestion could address this.

**No mid-level lapse rates.** Pressure-level temperatures (700, 500 hPa) are not reliably available from Open-Meteo gfs_seamless. v3 has no instability metric beyond CAPE.

**v1/v2 weights preserved.** The commitment formula weights and lifecycle thresholds are inherited from v1. They were derived against the static NJ CSV. Their suitability for atmospheric-input regimes is itself a hypothesis embedded in v3, not separately tested.

**Reference scales in feature normalization are heuristic.** The constants used for normalization (CAPE / 2500, precip / 5, shear / 15, pressure drop / 5, etc.) reflect domain conventions but are not learned from data. They may be wrong; their suitability is part of what v3 tests implicitly.

**Open-Meteo data quality.** Atmospheric observations from a single provider; no redundancy.

**On-demand pipeline execution.** Predictions accumulate hourly via Celery Beat (run-pipeline-hourly schedule).

---

## 12. What v3 Does Not Claim

- Predictive skill against any baseline.
- Cross-domain applicability.
- Validation of the underlying CI/CSO/MCC framework as a scientific theory.
- Demonstrated improvement over operational forecasting tools.
- Operational fitness for any decision-making context.
- That the new feature mappings in Section 7.4 are *correct* meteorology — only that they encode reasonable choices for testing the insufficient-inputs hypothesis.

---

## 13. Conditions for v4

A v4 model and corresponding pre-registration document will be required when any of the following changes:

- The atmospheric variable set (e.g., adding HRRR-derived helicity, lapse rates, true 0-6 km shear).
- Any normalization constant in Section 7.3-7.4.
- Any commitment formula weight or lifecycle threshold (Sections 7.5-7.6).
- The verification windows, event label, baselines, decision threshold, or sample-size requirements.

A v4 register does not invalidate v1, v2, or v3 results.

---

## 14. Implementation Plan

This document locks the v3 design. Implementation proceeds as follows:

1. Port v3 feature builder logic (Section 7.4) into a new file `backend/app/services/feature_builder_v3.py` (or augment existing feature_builder.py with versioned function).
2. Modify `engine_service.run_pipeline` to use the v3 feature builder when the active model version is `calibrator-v3.0`, with v2 logic preserved for v2-tagged calls if needed.
3. Insert a new `model_versions` row for `calibrator-v3.0` and set as default.
4. Verify implementation matches spec by comparing computed values against hand-calculated examples.
5. Run forward predictions; do NOT backfill against the April 27 - May 4 period.
6. Wait for verification record to accumulate; report metrics quarterly per Section 9.

The implementation step produces an **implementation pre-registration** that confirms the spec was implemented as locked, with the corresponding code commit hash. That commit hash anchors the v3 implementation cryptographically.

---

## 15. Lock and Provenance (DESIGN PHASE)

This document was written on the design lock date listed above and reflects the v3 design committed at that date. The git commit hash for this design document will be recorded here once committed.

When v3 implementation is complete, an implementation lock will be added as Section 16 with the implementation commit hash and a confirmation that the implemented code matches this spec.

---

## 16. Implementation Lock (PENDING)

*To be added when v3 implementation is complete and the implementation commit is made.*

---

## Section 16 — Implementation Lock
This section confirms that the v3 implementation matches the design specified in Sections 1–15 of this pre-registration, and locks the implementation to the methodology before any v3 prediction is verified.

  ##  16.1 Implementation Confirmation
    The v3 framework was implemented per Section 7.4 (feature derivations) verbatim. Specifically:

    backend/app/services/feature_builder_v3.py implements build_enriched_features_v3(df) and the v3 _compute_ct_v3(df, eps) helper. Each derived feature (storm_intensity_score, storm_transition_score, phase_transition_score, phase_prob_entropy, ci_confidence, stability, reliability) is computed from the locked formulas in Section 7.4 with no deviation.
    backend/app/services/engine_service.py was modified to import build_enriched_features_v3 (replacing the v1/v2 build_enriched_features) and to assemble the input DataFrame with the v3 atmospheric columns: cape, temperature_2m, dewpoint_2m, pressure_msl, wind_speed_10m, wind_speed_80m, wind_speed_180m, precipitation. The v1 feature builder is preserved unmodified for historical reproducibility of v1 and v2 results.
    A ModelVersion row was registered in the database with name calibrator-v3.0 and is now the default model version emitted by the pipeline. v2 predictions remain in the database tagged with calibrator-v2.0; v3 predictions are tagged with calibrator-v3.0. Verification queries can disambiguate by model_version_id.

  ##  16.2 End-to-End Verification
    The v3 pipeline was executed end-to-end via run_pipeline_all_locations_task after implementation lock. All six registered locations (Atco NJ, Birmingham AL, Dallas TX, Memphis TN, Newark HQ, Norman OK) produced CalibratedOutput rows tagged calibrator-v3.0 with commitment_probability values within the documented [0.05, 0.95] clip range. Lifecycle classification fired without error. No exceptions raised in worker logs.

  ##  16.3 Held-Out Integrity (Option A — Forward-Only Accumulation)
    The v3 pre-registration commits to forward-only accumulation for the verification population. v3 will not be back-scored against the historical atmospheric_observations rows that overlap v2's evaluation window. Reasoning:

    v2's verification result (locked under PRE_REGISTRATION_v2.md) and v3a's sub-test result (locked under RESULT_v3a_2026-05-04.md) were observed before v3's design was finalized. Backfilling v3 across that same window would contaminate the held-out evaluation: any tuning decision implicit in the v3 design, however slight, would have been informed by knowledge of v2's failure mode and the spatial structure that v3a explored.
    Forward-only accumulation preserves the property that v3's verification population is causally posterior to its design lock.

    The cost of this choice is calendar time: at six locations producing one prediction per hour, the v3 verification population reaches ~100 closed-window predictions per location at roughly 4–5 days of runtime. The first verification claim against v3 is therefore not expected before approximately 2026-05-18, after the primary 0–48 hour windows for the earliest v3 predictions have closed.

  ##  16.4 Provenance
    ItemReferencev3 design documentdocs/PRE_REGISTRATION_v3.md (this file)v3 feature builderbackend/app/services/feature_builder_v3.pyv3 pipeline integrationbackend/app/services/engine_service.pyv3 model version registrationModelVersion row, name calibrator-v3.0v3 default model flagset on registration dateEnd-to-end verificationAll six locations producing valid v3.0-tagged CalibratedOutput rowsImplementation lock commit(e811ddacbc3ceeca91a281f211be46f3d0da66ce)

  ##  16.5 Lock Statement
    The v3 implementation is locked as of the commit referenced in Section 16.4 above. Any subsequent change to the v3 feature builder, the v3 input variable list, the v3 commitment formula, the v3 clip bounds, the v3 lifecycle thresholds, or the v3 verification methodology constitutes a different model version (v3.1, v3.2, etc.) and requires its own pre-registration document.
    The v3 verification result, when produced, will be reported in a separate locked result document (docs/RESULT_v3_<date>.md) following the same discipline as RESULT_v3a_2026-05-04.md.

    End of Section 16 — Implementation Lock.

*End of Pre-Registration v3 (DESIGN).*