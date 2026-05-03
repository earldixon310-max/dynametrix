# Dynametrix Verification Pre-Registration — v2

**Version:** v2.0
**Model identifier:** `calibrator-v2.0`
**Lock date:** 2026-05-02
**Author:** Earl Dixon
**Status:** Locked. Any change to the items below constitutes a model version bump and requires a new pre-registration document.
**Supersedes verification of:** none. v2 generates its own verification record. v1 reliability data remains historical and is not retroactively reinterpreted.

---

## 1. Purpose

This document fixes, in advance of accumulated outcome data, the methodology by which Dynametrix's `commitment_probability` output under the v2 implementation will be evaluated for predictive skill. The verification windows, event label, baselines, and decision threshold are unchanged from v1 — what changes is the data flow and feature computation underlying the metric. This means v2 verification numbers are directly comparable against v1 verification numbers as a controlled test of whether real atmospheric inputs improve the framework's calibration.

This document does not make claims about v2's predictive performance. It describes how those claims will eventually be evaluated, against a verification record that begins accumulating at the lock date above.

---

## 2. Primary Verification Metric

**`commitment_probability`** — the scalar output produced by the v2 implementation of `run_pipeline` in `backend/app/services/engine_service.py` for a given location at a given time.

This metric is dimensionally identical to v1's `commitment_probability`. The formula that produces it is unchanged. What differs is the input data: under v2, the seven structural features feeding the formula are computed from real atmospheric observations for the calling location at the time of evaluation, not read from a static historical CSV.

All other quantities computed by the pipeline (CT, persistence, coherence_energy, trajectory_velocity, phase_transition_z, etc.) are explicitly **secondary diagnostics** for this verification register and are not themselves verification targets in v2.

---

## 3. Verification Windows

**Primary window:** 0–48 hours after the prediction's `observed_at` timestamp.

**Secondary window (also registered):** 0–24 hours after the prediction's `observed_at` timestamp.

Identical to v1.

---

## 4. Event Label

A binary outcome per prediction-window pair:

```
y = 1 if at least one SPC storm report (event_type ∈ {tornado, hail, wind})
        occurred within 50 km of the prediction location and within the
        verification window;
    0 otherwise.
```

**Ground truth source:** the `ground_truth_events` table populated by the daily SPC ingestion pipeline (`backend/app/services/storm_reports.py`).

**Spatial radius:** 50 km, computed via haversine great-circle distance.

**Coverage condition:** A prediction is included in the v2 register only when its full window falls within a date range for which ground-truth ingestion is complete.

Identical to v1.

---

## 5. Baselines

The four baselines from v1 are preserved exactly:

1. **Climatology** — constant forecast equal to the historical base rate at the location.
2. **Persistence** — today's `commitment_probability` set equal to the most recent prior day's `commitment_probability` for the same location.
3. **SPC Convective Outlook** — SPC's day-1 outlook category mapped to a probability.
4. **Atmospheric logistic baseline** — logistic regression on raw atmospheric inputs (CAPE, dewpoint depression, 0–6 km bulk shear when available, surface pressure tendency).

**Additional v2-specific baseline:**

5. **v1 baseline** — the v1 verification record from `calibrator-v1.0` over the same time window. v2 demonstrates added value if and only if its Brier score and reliability calibration improve over v1 on equivalent prediction-outcome pairs. Beating v1 is the *minimum* claim v2 needs to make to justify the additional engineering complexity.

A claim of "v2 has skill" requires positive Brier skill score against Baselines 1, 2, and 3 at minimum, AND demonstrably better calibration than Baseline 5 (v1).

---

## 6. Reported Statistics

For each baseline comparison, the following will be computed and published:

- Probability of Detection (POD) at decision threshold 0.5, with Wilson 95% CI
- False Alarm Ratio (FAR) at decision threshold 0.5, with Wilson 95% CI
- Critical Success Index (CSI) at decision threshold 0.5, with Wilson 95% CI
- Brier score
- Brier skill score against each baseline
- Reliability diagram with 10 probability bins
- Sample size per bin and confidence intervals

Statistics will be reported when sample size exceeds 100 verified predictions per location-window combination. Below that threshold, statistics are marked "preliminary" and confidence intervals reported but no skill claims made.

Identical to v1.

---

## 7. Formula and Pipeline Specification — `calibrator-v2.0`

`commitment_probability` under v2 is produced by the following deterministic pipeline. Each stage is explicitly named so a reviewer can reproduce the computation from the same inputs.

### 7.1 Input data flow

Per pipeline call (location L, time T):

1. Query the `atmospheric_observations` table for all rows where `location_id = L` and `observed_at` is in the window `[T - 96 hours, T]`.
2. Filter to `observed_at <= now_utc` (only past observations; forecast hours are excluded from feature computation).
3. Sort ascending by `observed_at`.
4. Require at least 8 observations; if fewer, the pipeline returns no output and writes no CalibratedOutput row.

The atmospheric_observations rows are populated by the Open-Meteo ingestion pipeline (`backend/app/services/atmospheric_ingestion.py`) using the `gfs_seamless` model, which blends GFS Global with HRRR where available (US locations).

### 7.2 Column mapping for feature builder input

The feature builder expects three named columns. The mapping from atmospheric_observations to those columns:

| Feature builder column | atmospheric_observations source | Notes |
|---|---|---|
| `precip_mm` | `precipitation` | Open-Meteo hourly precipitation in mm |
| `surface_pressure_hPa` | `pressure_msl` | **Documented substitution.** pressure_msl is sea-level-adjusted; surface and MSL pressure differ by a roughly constant location-dependent offset. The framework consumes pressure *changes* (`pressure_drop_3h`), which are equivalent under this substitution. |
| `temp_C` | `temperature_2m` | Direct match |

If `precipitation` is null for a given hour, it is treated as 0.0 mm.

### 7.3 Feature builder transformation chain

Implemented in `backend/app/services/feature_builder.py` as `build_enriched_features(df)`. The transformation chain produces, for the most recent row in the input DataFrame, the seven structural features the v1 commitment formula consumes.

**Stage 1 — Basic aggregations:**

```
storm_intensity_score   = precip_mm.rolling(3h, min_periods=1).mean()
pressure_drop_3h        = -1 × (pressure_msl.diff(3))                  [fillna 0]
temp_trend_3h           = temperature_2m.diff(3)                       [fillna 0]
```

**Stage 2 — Storm transition:**

```
storm_transition_score  = normalize_to_0_1(|pressure_drop_3h|)
```

where `normalize_to_0_1(s) = s / max(|s|)` clipped to [0,1].

**Stage 3 — CI / stability / reliability:**

```
ci_raw                  = |pressure_drop_3h|.rolling(3h, min_periods=1).mean()
ci_confidence           = clip(normalize_to_0_1(ci_raw), 0, 1)
stability               = clip(1 / (1 + |pressure_drop_3h|), 0, 1)
reliability_raw         = ci_confidence.rolling(3h, min_periods=1).mean()
reliability             = clip(normalize_to_0_1(reliability_raw), 0, 1)
```

**Stage 4 — Entropy and phase mix:**

```
precip_flag             = (precip_mm > 0.1).astype(float)
temp_flip               = |temp_trend_3h.diff()|                       [fillna 0]
press_var               = |pressure_drop_3h|

entropy_raw             = 0.45 · precip_flag.rolling(3h).mean()
                        + 0.30 · normalize_to_0_1(|temp_flip|)
                        + 0.25 · normalize_to_0_1(|press_var|)

phase_prob_entropy      = clip(entropy_raw, 0, 1)

phase_mix_score_3h      = clip(0.5 · precip_flag.rolling(3h).mean()
                              + 0.5 · normalize_to_0_1(temp_flip), 0, 1)
phase_mix_score_6h      = clip(phase_mix_score_3h.rolling(2h).mean(), 0, 1)
```

**Stage 5 — Phase transition:**

The phase transition score detects structural change rather than absolute level. It uses derivatives and second derivatives of the Stage 3/4 features:

```
ci_slope                = |ci_confidence.diff()|
stability_drop          = max(0, -stability.diff())
reliability_drop        = max(0, -reliability.diff())
entropy_rise            = max(0, phase_prob_entropy.diff())
mix_rise                = max(0, max(phase_mix_score_3h, phase_mix_score_6h).diff())
ci_accel                = |ci_slope.diff()|
entropy_accel           = max(0, entropy_rise.diff())

raw_transition          = 0.28 · ci_slope
                        + 0.24 · stability_drop
                        + 0.18 · reliability_drop
                        + 0.14 · entropy_rise
                        + 0.10 · mix_rise
                        + 0.04 · ci_accel
                        + 0.02 · entropy_accel

raw_transition_smooth   = raw_transition.rolling(3h, min_periods=1).mean()
transition_z            = robust_zscore(raw_transition_smooth, window=24h)
                          [median/MAD-based, min_periods=8]
transition_score        = clip(max(0, transition_z) / 3.0, 0, 1)

context_gate            = clip(0.6 · ci_confidence + 0.4 · storm_transition_score, 0, 1)
phase_transition_score  = clip(transition_score · (0.5 + 0.5 · context_gate), 0, 1)
```

### 7.4 Coherence Tension (CT) — diagnostic only

```
instability             = 0.50 · phase_transition_score
                        + 0.30 · storm_transition_score
                        + 0.20 · storm_intensity_score

competition             = 0.70 · phase_prob_entropy
                        + 0.30 · phase_mix_score_3h

persistence             = clip(0.45 · stability + 0.35 · reliability + 0.20 · ci_confidence, 0.05, ∞)

CT                      = (instability · competition) / sqrt(persistence + 1e-8)
CT_threshold            = 97th percentile of CT across the input window
CT_high                 = CT >= CT_threshold
```

CT is computed and stored but is **not** part of the verification target. It is a secondary diagnostic for explaining commitment_probability movements.

### 7.5 v1 commitment formula — applied to the most recent row

After the feature builder runs over the input DataFrame, the pipeline takes the **last row** (most recent observation) and applies the unchanged v1 commitment formula:

```
organization            = 0.35 · phase_transition_score
                        + 0.25 · storm_transition_score
                        + 0.20 · storm_intensity_score
                        + 0.10 · phase_prob_entropy
                        + 0.10 · ci_confidence

commitment_probability  = clip(0.18 + 0.70 · organization, 0.05, 0.95)

confidence              = clip(0.25 + 0.35 · ci_confidence
                                    + 0.20 · reliability
                                    + 0.20 · stability,
                               0.05, 0.95)
```

### 7.6 Lifecycle classification — unchanged from v1

```
if commitment_probability ≥ 0.68:           lifecycle = commitment;        lead = 6h
elif commitment_probability ≥ 0.50:         lifecycle = pre_commitment;    lead = 12h
elif phase_transition_score > 0.65 and storm_transition_score > 0.25:
                                            lifecycle = reconfiguration;   lead = null
elif commitment_probability < 0.30:         lifecycle = decay;             lead = null
else:                                       lifecycle = quiet;             lead = null
```

### 7.7 Secondary derived metrics — unchanged from v1

```
persistence            = clip((stability + reliability + ci_confidence) / 3, 0, 1)
coherence_energy       = clip(0.45·phase_transition_score + 0.25·storm_transition_score
                              + 0.15·storm_intensity_score + 0.15·ci_confidence, 0, 1)
trajectory_velocity    = clip(|coherence_energy − persistence|, 0, 1)
```

These weights, thresholds, and the stage definitions above constitute the registered v2 model. Any change to any constant is a model version bump.

---

## 8. Decision Threshold

Decision threshold for binary classification: **0.5**. Outcomes are stored in `verification_outcomes` parameterized by `decision_threshold`, allowing later evaluation at thresholds 0.3, 0.5, and 0.7 in parallel without modifying historical records. The 0.5 threshold is the registered headline; others are reported as supplementary.

Identical to v1.

---

## 9. Sample Size and Reporting Cadence

Verification statistics are computed and published quarterly, beginning the calendar quarter following 100 verified predictions per location. Statistics with sample size below 100 are marked "preliminary" and not used for skill claims.

The `verification_outcomes` table is append-only at the `(calibrated_output_id, decision_threshold)` level.

Identical to v1.

---

## 10. Known Limitations of v2

The v2 register documents the framework as it actually exists at lock date. The following limitations are flagged explicitly so that the verification record is interpreted correctly.

**Limited input variable set.** The v1 feature builder operates on three raw weather inputs: precipitation, pressure, and temperature. It does not consume CAPE, wind shear, helicity, dewpoint, lapse rates, precipitable water, or other variables that operational severe-weather forecasting relies on. The framework is therefore tested on a restricted information substrate. A future v3 could expand the feature builder to consume additional atmospheric inputs.

**pressure_msl substitution.** As documented in Section 7.2, the feature builder receives sea-level-adjusted pressure (`pressure_msl`) where its original implementation expected surface pressure (`surface_pressure_hPa`). Because the framework consumes pressure *changes*, this substitution preserves the dynamics for a fixed location but introduces a roughly constant offset in absolute pressure values that the framework does not consume.

**Hardcoded weights from the v1 era.** The weights and thresholds in the v1 commitment formula (Section 7.5), lifecycle classification (Section 7.6), and feature builder transformation chain (Section 7.3) were chosen during development of `calibrator-v1.0` against a static training dataset. They are not learned from atmospheric_observations data and have not been re-fit since v1. v2 inherits these constants; whether they are appropriate for the new input distribution is itself an empirical question that the verification record will eventually answer.

**Open-Meteo data quality.** Atmospheric observations are sourced from a single provider (Open-Meteo `gfs_seamless` model). Data outages, model bias, or specific variable unavailability for some locations propagate into the pipeline as missing or null inputs that the feature builder treats as zero or skip-imputes. A future version could ingest from multiple providers for redundancy and bias reduction.

**24-hour rolling z-score requires history.** The phase transition z-score uses a 24-hour rolling median/MAD baseline with `min_periods=8`. Locations with less than 8 hours of contiguous past observations produce no v2 output. For locations that have less than 24 hours, the z-score is valid but noisier than for locations with full history.

**On-demand pipeline execution.** v2 runs only when triggered by a user-initiated refresh or scheduled task. `commitment_probability` values are therefore fresh as of the most recent refresh, not continuously updated. The verification record reflects the actual freshness of each prediction at its `observed_at` timestamp.

---

## 11. What v2 Does Not Claim

Registering v2 makes none of the following claims:

- Predictive skill against climatology, persistence, SPC outlook, atmospheric logistic baseline, or v1.
- Cross-domain applicability (weather, gravitational waves, finance, neuroscience).
- Validation of the underlying CI/CSO/MCC framework as a scientific theory.
- Demonstrated improvement over operational forecasting tools.
- Operational fitness for any decision-making context. Dynametrix is a research instrument under registered evaluation; it is not a forecast or warning system.

What v2 *does* register is the methodology by which all of the above can eventually be tested.

---

## 12. Conditions for v3

A v3 model and corresponding new pre-registration document will be required when any of the following changes:

- The formula in Section 7 (any constant, weight, threshold, or transformation in the feature builder, CT, commitment formula, or lifecycle classification).
- The data source for input features (e.g., switching from Open-Meteo to HRRR-direct, or adding additional providers).
- The set of input variables consumed by the feature builder (currently precip, pressure, temperature; v3 might add CAPE, shear, dewpoint, etc.).
- The feature builder transformation chain itself (any change in how Stage 1–5 operations work).
- The verification windows, event label, baselines, decision threshold, or sample-size requirements registered above.

A v3 register does not invalidate v1 or v2 results. Each version produces its own historical reliability record, comparable on equivalent prediction-outcome pairs.

---

## 13. Lock and Provenance

This document was written on the lock date listed above and reflects the system state at that date. The corresponding code state can be reconstructed from:

- `backend/app/services/engine_service.py` — v2 `run_pipeline` implementation that queries `atmospheric_observations`, calls the feature builder, and applies the v1 commitment formula
- `backend/app/services/feature_builder.py` — v1 weather feature builder ported into the production codebase, unchanged from the original `feature_builder.py` reference implementation
- `backend/app/services/atmospheric_ingestion.py` — Open-Meteo ingestion service producing atmospheric_observations rows
- `backend/app/db/models/engine.py` — `AtmosphericObservation` model definition, including the `precipitation` column added at v2 lock
- `backend/app/workers/tasks.py` — `run_pipeline_task` updated to pass `db` and `location.id` to the v2 pipeline

Together these define `calibrator-v2.0` as the registered model.

The git commit hash for v1 was `48f0cc2`. The v2 commit hash will be recorded when this document is committed.

---

*End of Pre-Registration v2.*