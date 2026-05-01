# Dynametrix Verification Pre-Registration — v1

**Version:** v1.0
**Model identifier:** `calibrator-v1.0`
**Lock date:** 2026-05-02
**Author:** Earl Dixon
**Status:** Locked. Any change to the items below constitutes a model version bump and requires a new pre-registration document.

---

## 1. Purpose

This document fixes, in advance of accumulated outcome data, the methodology by which Dynametrix's `commitment_probability` output will be evaluated for predictive skill. It is designed to satisfy the falsifiability principle: the conditions under which the framework would be declared to lack skill are stated in advance and are empirically observable.

This document does **not** make claims about the framework's predictive performance. It describes how those claims will eventually be evaluated, against a record that is currently being accumulated.

---

## 2. Primary Verification Metric

**`commitment_probability`** — the scalar output produced by the `run_pipeline` function in `backend/app/services/engine_service.py` for a given location at a given time.

This is the value that will be tested for calibration and skill. All other quantities computed by the pipeline (CT, RST, PCA trajectory metrics, phase entropy, persistence, coherence energy, trajectory velocity) are explicitly **secondary diagnostics** for this verification register and are not themselves verification targets in v1.

---

## 3. Verification Windows

**Primary window:** 0–48 hours after the prediction's `observed_at` timestamp.

**Secondary window (also registered):** 0–24 hours after the prediction's `observed_at` timestamp.

Reliability and skill metrics will be reported at both windows. The primary window is the headline number; the secondary window is reported alongside.

---

## 4. Event Label

A binary outcome per prediction-window pair:

```
y = 1 if at least one SPC storm report (event_type ∈ {tornado, hail, wind})
        occurred within 50 km of the prediction location and within the
        verification window;
    0 otherwise.
```

**Ground truth source:** the `ground_truth_events` table populated by the daily SPC ingestion pipeline (see `backend/app/services/storm_reports.py`). Reports are sourced from the Storm Prediction Center's daily filtered CSV products (`https://www.spc.noaa.gov/climo/reports/`).

**Spatial radius:** 50 km, computed via haversine great-circle distance from the prediction location's lat/lon.

**Coverage condition:** A prediction is included in the verification record only when its full window falls within a date range for which ground-truth ingestion is complete. Predictions with partial or absent ground-truth coverage are excluded from the v1 register.

---

## 5. Baselines

The following four baselines are pre-registered for comparison. `commitment_probability` will be evaluated against each, on the same prediction-outcome pairs.

**Baseline 1 — Climatology.** A constant forecast equal to the historical base rate of severe-weather events at the location's grid cell, computed from at least 5 years of NCEI Storm Events archive data when available, or from the accumulated `ground_truth_events` record otherwise.

**Baseline 2 — Persistence.** Today's `commitment_probability` set equal to the most recent prior day's `commitment_probability` for the same location.

**Baseline 3 — SPC Convective Outlook.** SPC's day-1 outlook category for the location's region, mapped to a probability via the SPC-published category-to-probability table (general thunderstorm 0.05, marginal 0.10, slight 0.15, enhanced 0.30, moderate 0.45, high 0.60).

**Baseline 4 — Atmospheric logistic baseline.** A logistic regression on raw atmospheric inputs (CAPE, dewpoint depression, 0–6 km bulk shear when available, surface pressure tendency) trained on the verification record itself with appropriate held-out splits, fit on data prior to the evaluation period.

A claim of "skill" requires positive Brier skill score against Baselines 1, 2, and 3 at minimum. Beating Baseline 4 is a stronger claim and will be reported separately.

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

Statistics will be reported when sample size exceeds 100 verified predictions per location-window combination. Below that threshold, statistics will be marked as "preliminary" and confidence intervals reported but no skill claims made.

---

## 7. Formula Specification — `calibrator-v1.0`

`commitment_probability` is computed deterministically by the following formula in `backend/app/services/engine_service.py:run_pipeline`:

**Inputs (per pipeline call):** seven precomputed features read from a single row of the input dataset (see Section 10):

| Symbol | Source column | Meaning |
|---|---|---|
| φ | `phase_transition_score` | Phase transition indicator |
| τ | `storm_transition_score` | Storm transition pressure |
| ι | `storm_intensity_score` | Storm intensity proxy |
| ε | `phase_prob_entropy` | Phase probability entropy |
| κ | `ci_confidence` | Constraint-intelligence confidence |
| σ | `stability` | Stability score |
| ρ | `reliability` | Reliability score |

**Organization composite:**

```
organization = 0.35·φ + 0.25·τ + 0.20·ι + 0.10·ε + 0.10·κ
```

**Commitment probability:**

```
commitment_probability = clip(0.18 + 0.70·organization, 0.05, 0.95)
```

**Confidence:**

```
confidence = clip(0.25 + 0.35·κ + 0.20·ρ + 0.20·σ, 0.05, 0.95)
```

**Lifecycle classification (hierarchical):**

```
if commitment_probability ≥ 0.68:           lifecycle = commitment;        lead = 6h
elif commitment_probability ≥ 0.50:         lifecycle = pre_commitment;    lead = 12h
elif φ > 0.65 and τ > 0.25:                 lifecycle = reconfiguration;   lead = null
elif commitment_probability < 0.30:         lifecycle = decay;             lead = null
else:                                       lifecycle = quiet;             lead = null
```

**Secondary derived metrics (for diagnostic display only, not part of verification):**

```
persistence          = (σ + ρ + κ) / 3
coherence_energy     = clip(0.45·φ + 0.25·τ + 0.15·ι + 0.15·κ, 0, 1)
trajectory_velocity  = clip(|coherence_energy − persistence|, 0, 1)
```

These weights and thresholds, taken together, constitute the registered v1 model. Any change to any constant above is a model version bump.

---

## 8. Decision Threshold

The decision threshold for binary classification (used in POD/FAR/CSI computation) is fixed at **0.5**. Outcomes are also stored in the `verification_outcomes` table parameterized by `decision_threshold`, allowing later evaluation at thresholds 0.3, 0.5, and 0.7 in parallel without modifying historical records. The 0.5 threshold is the registered headline; the others are reported as supplementary.

---

## 9. Sample Size and Reporting Cadence

Verification statistics will be computed and published quarterly, beginning the calendar quarter following 100 verified predictions per location. Statistics with sample size below 100 are marked "preliminary" and not used for skill claims.

The verification record (the `verification_outcomes` table) is append-only at the (calibrated_output_id, decision_threshold) level. Outcomes are not modified after being written. Re-evaluation at different thresholds creates new rows; it does not overwrite existing rows.

---

## 10. Known Limitations of v1

The v1 register documents the framework as it actually exists at lock date. The following limitations are flagged explicitly so that the verification record is interpreted correctly. None of these constitute a basis for revising v1 reliability numbers after the fact; they are honest disclosures of what is being tested.

**Static input dataset.** The `run_pipeline` function reads precomputed structural features from a single static CSV (`backend/tools/hourly_weather_nj_2026_01_22_26_enriched.csv`) representing weather observations from northern New Jersey, January 22–26, 2026. It does **not** read from the `atmospheric_observations` table populated by the Open-Meteo ingestion pipeline.

**Per-location cursor cycling.** Each location maintains a cursor file that tracks its position within the static CSV. Successive calls advance the cursor and wrap modulo the CSV length. Different locations therefore receive different rows from the same dataset rather than location-specific atmospheric data.

**Implication.** The v1 pipeline is not, in its current implementation, responsive to actual atmospheric conditions at any specific location. Predictions for Newark, Atco, Norman, Dallas, Memphis, and Birmingham are all derived from cycling cursor positions through the same Northern New Jersey, January 2026 dataset. Verification statistics computed against this version are expected to show limited or no skill above climatology, and any apparent skill should be interpreted with this in mind.

**v1 verification serves as a baseline.** The purpose of locking v1 is to establish a documented baseline against which a planned v2 (with atmospheric_observations integrated as live input) will be evaluated. A v2 reliability measurement showing improvement over v1 would be empirical evidence that the atmospheric integration adds skill.

---

## 11. What v1 Does Not Claim

The following claims are **not** made by registering v1:

- Predictive skill against climatology, persistence, or any baseline.
- Cross-domain applicability (weather, gravitational waves, finance, neuroscience).
- Validation of the underlying CI/CSO/MCC framework as a scientific theory.
- Connection between `commitment_probability` and any specific atmospheric process at the prediction's location, beyond the structural features encoded in the static input dataset.
- Operational fitness for any decision-making context. Dynametrix is a research instrument under registered evaluation; it is not a forecast or warning system.

---

## 12. Conditions for v2

A v2 model and corresponding new pre-registration document will be required when any of the following changes:

- The formula in Section 7 (any constant, weight, threshold, or transformation).
- The data source for input features (e.g., switching from the static CSV to live atmospheric_observations).
- The set of input features (adding, removing, or replacing any of the seven listed features).
- The lifecycle classification rules (any threshold or conditional).
- The verification windows, event label definition, baselines, or decision threshold registered above.

A v2 register does not invalidate v1 results. Each version produces its own historical reliability record.

---

## 13. Lock and Provenance

This document was written on the lock date listed above and reflects the system state at that date. The corresponding code state can be reconstructed from:

- `backend/app/services/engine_service.py` — formula and pipeline implementation
- `backend/tools/hourly_weather_nj_2026_01_22_26_enriched.csv` — input dataset
- `backend/tools/train_weather_commitment_calibrator.py` — currently a stub; weights are hardcoded in `engine_service.py`, not loaded from a trained artifact

Together these define `calibrator-v1.0` as the registered model.

---

*End of Pre-Registration v1.*