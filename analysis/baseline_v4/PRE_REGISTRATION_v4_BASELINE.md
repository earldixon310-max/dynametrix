# Pre-registration v4 BASELINE v2 — Generic statistical baseline for severe weather forecasting at v4 locations

**Status:** Draft pending lock commit.
**Identifier:** `pre-registration-v4-baseline-v2`
**Companion to:** `pre-registration-v4` (locked at commit `01c35ba`)
**Supersedes:** `pre-registration-v4-baseline-v1` (locked at commit `16aa167`), retired due to logistic regression convergence failure on unscaled features. v1 remains in the historical record but its model artifacts are not used.
**Date:** 2026-05-17.
**Author:** Earl Dixon.

---

## 1. Hypothesis

A deliberately simple statistical model fitted on the same raw atmospheric inputs that calibrator-v3.0 consumes will produce calibrated and skilled severe-weather predictions at the six v4 locations across both severe-weather regimes (Great Plains and Ohio Valley).

This pre-registration is the companion evaluation to v4 (`pre-registration-v4`, locked at `01c35ba`). It is not a re-test of v3.0; it is a benchmark that v3.0's performance will be measured against. Together v4 and v4-baseline produce the data needed to answer the value-add question: **does v3.0's calibration mechanism extract signal from atmospheric inputs that generic statistical methods do not?**

The baseline's own outcome is recorded under the same regime-partitioned classification used by v4 (Section 6). The comparison between v3.0 and baseline is itself a pre-registered analysis specified in Section 7 of this document.

---

## 2. System under evaluation

**Primary model:** L2-regularized logistic regression with feature standardization. Features are mean-centered and scaled to unit variance via `sklearn.preprocessing.StandardScaler` before being passed to logistic regression. Regularization strength `C` is selected by time-series cross-validation within the training window (5-fold split, ROC-AUC scoring). Implementation: `sklearn.pipeline.Pipeline([StandardScaler, LogisticRegressionCV])`. The StandardScaler step is required for the L2-regularized logistic regression's optimizer to converge on features at vastly different natural scales (CAPE in J/kg, temperature in K, precipitation in mm, pressure in Pa, wind components in m/s). The v1 lock at commit `16aa167` omitted this preprocessing step and the optimizer failed to converge; v2 corrects this.

**Auxiliary model:** Gradient-boosted tree, deliberately bounded in complexity: `max_depth=4`, `n_estimators=200`, `learning_rate=0.05`, no hyperparameter search. Implementation: `sklearn.ensemble.GradientBoostingClassifier`. Reported alongside the primary as a secondary diagnostic; the logistic regression is the registered comparison model.

**Feature construction.** Raw atmospheric variables from the `atmospheric_observations` table at v4-baseline lock time. The exact column list is enumerated in Section 3.3. Engineered features applied per location-hour:

- Current value of each atmospheric variable.
- Rolling mean over 3, 6, 12, and 24-hour trailing windows.
- Rolling standard deviation over 3, 6, 12, and 24-hour trailing windows.
- First differences over 1, 3, and 6-hour intervals.

Total feature count is fixed by the column list at lock time × 12 (1 current + 4 means + 4 stds + 3 diffs). Documented exactly in the analysis code at lock.

**Prediction.** Per location, per hour: the trained model outputs `P(severe_event ∈ [T, T+48h] within 50km)`. Same prediction target as v3.0 and v4.

**No part of v3.0, v3.0's feature builder, or v3.0's outputs is consumed by the baseline.** The baseline operates entirely on raw atmospheric variables, transformed only by the generic rolling-window features above.

---

## 3. Test data

### 3.1 Training data

**Source:** Existing `atmospheric_observations` and `ground_truth_events` rows for the six locations covered by v3 (including Norman OK), for the period from earliest available record through 2026-05-17 (v4 lock date).

**Rationale:** Training on existing v3 locations and evaluating on the new v4 locations tests whether atmospheric inputs alone — without location-specific tuning — generalize across geography. This complements v4's regime-generalization framing; the baseline asks whether generic methods generalize, while v4 asks whether the framework generalizes.

**Window:** All training data must precede the v4-baseline lock commit by at least 1 hour to prevent any temporal leakage.

**Snapshot:** Training data is materialized as a CSV (`baseline_v4_training_set.csv`) and SHA-256 hashed at setup time. The hash is committed to this pre-registration before the lock commit, locking the training set in the same way v4's test data is locked.

### 3.2 Evaluation data

**Locations:** The six v4 locations, identified by the UUIDs locked in `pre-registration-v4` Section 3:

1. Wichita, KS — `29172590-f05d-483c-b213-b851421e47ff`
2. Omaha, NE — `96ffa380-69ff-472e-9418-d981e695cf81`
3. Dodge City, KS — `7e37c63e-4cc2-4ea7-a539-c50fea99f683`
4. Nashville, TN — `d76fc5a1-e2b9-4662-89b4-1b1499ff3201`
5. Louisville, KY — `a26d4e34-4baf-463b-af98-1d28c54e3b9d`
6. Cincinnati, OH — `3885e98e-966c-48f3-86af-d4386cbc6cb1`

**Window:** Same 90-day accumulation window as v4, from the v4-baseline lock commit. The baseline begins predicting hourly from its lock commit forward, on the same evaluation grid that v4 uses.

**Ground truth:** Same NWS SPC daily storm reports as v4 (event types: severe wind ≥ 58 mph, hail ≥ 1 inch, tornado any rating), ingested daily at 14:00 UTC into `ground_truth_events`.

**Sample-size threshold:** The baseline result document binds at 90 days elapsed from the v4-baseline lock commit. No early-exit on sample size. Concurrent with v4's lock.

### 3.3 Atmospheric variable column list

The 10 atmospheric variables consumed by the baseline. These are the columns from `atmospheric_observations` that are actually populated by the existing v3 atmospheric ingestion pipeline at v4-baseline lock. The schema declares additional columns (see note below) that are not currently populated and are therefore not available to either v3.0 or to the baseline:

1. `cape` — Convective Available Potential Energy
2. `temperature_2m` — 2-meter air temperature
3. `dewpoint_2m` — 2-meter dewpoint
4. `relative_humidity_2m` — 2-meter relative humidity
5. `pressure_msl` — mean sea-level pressure
6. `wind_speed_10m` — 10-meter wind speed
7. `wind_direction_10m` — 10-meter wind direction
8. `wind_speed_80m` — 80-meter wind speed
9. `wind_direction_80m` — 80-meter wind direction
10. `precipitation` — precipitation

**Atmospheric columns declared in the schema but not populated by the current ingestion** (and therefore not consumed by either v3.0 or the baseline): `lifted_index`, `convective_inhibition`, `temperature_500hPa`, `temperature_700hPa`, `temperature_850hPa`, `precipitable_water`, `wind_speed_180m`, `wind_direction_180m`. The absence of these variables limits both v3.0 and the baseline equally, preserving the fairness of the comparison. Expanding the ingestion to populate these variables is operational work separate from this pre-registration and would, if undertaken, become a v4-baseline-v2 evaluation rather than a modification of this one.

**Wind variable preprocessing.** Wind directions are circular (359° is adjacent to 1°) and would degrade the predictive performance of any linear model fed them as raw degrees. Before feature construction, each (wind_speed, wind_direction) pair at each populated level is converted to (u, v) wind components:

```
u = wind_speed × sin(wind_direction × π / 180)
v = wind_speed × cos(wind_direction × π / 180)
```

This is the standard meteorological transformation producing physically meaningful east-west and north-south wind components. The conversion is deterministic and applies identically to training and evaluation data. The raw `wind_speed_*` and `wind_direction_*` columns are NOT used as features in their original form after this conversion; only the (u, v) components enter feature construction.

**Effective base-feature count after wind decomposition: 10.** Composed of: 1 instability metric (CAPE) + 4 surface variables (T2m, Td2m, RH2m, Pmsl) + 4 wind components (u and v at 10m, 80m) + 1 precipitation = 10.

**Total feature count: 120.** Per base variable: 1 current value + 4 rolling means (3, 6, 12, 24h windows) + 4 rolling standard deviations (same windows) + 3 first differences (1, 3, 6h intervals) = 12 engineered features. 10 base × 12 engineered = 120 total features per location-hour.

The schema state and the set of populated columns at v4-baseline lock are both bound. Any subsequent schema migration or ingestion expansion does not retroactively change what v4-baseline tests.

---

## 4. Methodology

**Training.** The primary model and the auxiliary model are fitted once, immediately after the v4-baseline lock commit, using the materialized training set. Hyperparameters and any internal cross-validation procedure are bound by Section 2. The trained model artifacts (logistic regression coefficients, GBT parameters) are committed alongside the analysis code at the lock commit. No re-training or re-fitting is permitted between the lock commit and the result commit.

**Prediction.** Hourly, per location, the trained models produce calibrated probabilities for each of the six v4 locations from v4-baseline lock forward.

**Verification matching.** Identical to v4 Section 4: prediction at time T matched to qualifying SPC event with `event_at` ∈ [T, T+48h] within 50 km haversine distance.

**Per-regime pooling and binning.** Identical to v4 Section 4. Predictions are partitioned by regime (Plains: locations 1–3; Ohio Valley: locations 4–6) and analyzed separately. 10 equal-width bins on [0, 1], n ≥ 30 inclusion threshold per bin.

**Per-bin Wilson interval.** Identical to v4 Section 4.

**Per-regime Brier skill score.** Identical to v4 Section 4. BSS computed against per-location base-rate climatology over the accumulation window. Per-regime BSS uses only the three locations in that regime.

---

## 5. Decision criteria (baseline's own outcome)

Per-regime criteria, applied independently to each of the two regimes:

(a) **Reliability:** At least 6 of populated bins (n ≥ 30) pass the Wilson criterion.

(b) **Skill:** Per-regime BSS > 0.

The baseline's regime-level outcome is "calibrated and skilled" if both (a) and (b) hold for that regime. The baseline's aggregate outcome under v4's regime-generalization framing is classified per Section 6, identical to v4's classification table.

---

## 6. Outcome classification (baseline)

The baseline's outcome is recorded under the same four-cell classification as v4:

| Plains regime | Ohio Valley regime | Outcome |
|---|---|---|
| Calibrated and skilled | Calibrated and skilled | **BASELINE: REGIME-GENERAL** |
| Calibrated and skilled | Not calibrated or not skilled | **BASELINE: PLAINS-ONLY** |
| Not calibrated or not skilled | Calibrated and skilled | **BASELINE: OHIO VALLEY ONLY** |
| Not calibrated or not skilled | Not calibrated or not skilled | **BASELINE: NEITHER** |

This is the baseline's standalone outcome, recorded irrespective of v4. The v3.0-vs-baseline comparison is specified separately in Section 7.

---

## 7. v3.0-vs-baseline comparison (pre-registered)

This section pre-registers the comparison between v3.0's v4 outcome and the baseline's outcome. The comparison is conducted once, at the same time both result documents are locked (after both 90-day windows elapse and converge).

### 7.1 Value-add criterion

**v3.0 demonstrates positive value-add over generic statistical methods if BOTH:**

(a) v3.0's per-regime BSS exceeds the baseline's per-regime BSS by at least ΔBSS > 0.05 in at least one regime.

(b) v3.0's reliability outcome is not worse than the baseline's reliability outcome in any regime (i.e., v3.0 does not pass fewer reliability bins than the baseline in either regime).

### 7.2 Comparison outcome classification

| v3.0 outcome (v4) | Baseline outcome | Comparison verdict |
|---|---|---|
| Better than baseline in ≥1 regime by ΔBSS > 0.05 AND reliability never worse | (any) | **V3.0 ADDS SIGNAL** — calibrator-v3.0's transformations extracted useful predictive structure beyond what generic statistical methods extracted from the same atmospheric inputs, under the operational conditions and over the evaluation window of this test |
| Equivalent to baseline (no regime where ΔBSS > 0.05) | (any) | **V3.0 NULL VALUE-ADD** — v3.0's calibrated outputs are statistically indistinguishable from those a generic logistic regression produces on the same inputs, under the operational conditions and over the evaluation window of this test |
| Worse than baseline in any regime (negative ΔBSS at any regime) | (any) | **V3.0 DESTROYS SIGNAL** — v3.0's transformations actively reduced predictive information present in the atmospheric inputs, under the operational conditions and over the evaluation window of this test |

The comparison verdict is recorded as a separate section in the v4 result document, citing both v4's locked outcome and v4-baseline's locked outcome. The verdict is not subject to revision after both result documents are locked.

### 7.3 Interpretive constraints on the comparison verdict

The comparison verdict is bounded to what it actually tested. The v4 result document, when recording the comparison verdict, MUST observe the following interpretive constraints:

**A V3.0 ADDS SIGNAL verdict establishes:**

- That calibrator-v3.0's transformations extracted predictive structure beyond what these specific baseline models extracted from the same atmospheric inputs, at these six locations, over this 90-day window, against the registered ground-truth definition.

**A V3.0 ADDS SIGNAL verdict does NOT establish:**

- That the calibrator-v3.0 mechanism generalizes to other locations, other windows, other forecast targets, or other event definitions.
- That alternative baseline model classes (random forests, neural networks, established severe-weather composites such as SCP/STP/EHI) would have produced the same comparison.
- That the predictive structure extracted reflects any specific physical or conceptual interpretation of "coherence," "structural commitment," "MCC/CI," or related framework vocabulary. The test measures predictive accuracy under the registered criteria; it does not test any interpretation of why the predictions work.
- That the framework conceptually underlying calibrator-v3.0 is a correct description of severe-weather organization, atmospheric dynamics, or any broader claim about reality.

**A V3.0 NULL VALUE-ADD or V3.0 DESTROYS SIGNAL verdict establishes:**

- That under these operational conditions, calibrator-v3.0 did not (or actively reduced) extract predictive structure beyond the registered baselines. The verdict applies to this specific operationalization at these specific locations over this specific window.

**A V3.0 NULL VALUE-ADD or V3.0 DESTROYS SIGNAL verdict does NOT establish:**

- That a different operationalization of the framework's conceptual program would necessarily produce the same result.
- That the framework's conceptual program is invalid in domains, scales, or measurement settings other than this one.

**Required disclosures.** The v4 result document MUST disclose:

- That training data sources differ (baseline trained on existing v3 locations; v3.0 is the calibrator-v3.0 artifact fitted under v3's locked methodology).
- That the comparison is between two specific operationalizations, not between two general approaches; equivalence or superiority of one over the other does not generalize beyond the registered conditions.
- That any meaningful comparison requires both regimes to have accumulated sufficient sample size; if either regime falls below 100 verified pairs, the comparison MUST be flagged as underpowered.

---

## 8. Operational notes

**Training-set immutability.** The training CSV materialized at setup is locked at the baseline commit. Re-running the analysis must verify the training-set SHA-256 matches the locked hash, or refuse to proceed.

**Model artifact immutability.** Trained model parameters (logistic regression coefficients, GBT trained model bytes) committed at lock. Re-running prediction uses the locked model, never re-fits.

**Pipeline integrity.** Hourly prediction runs continuously between v4-baseline lock and v4-baseline result commit. Outages MUST be disclosed in the result document identically to v4.

**Modifications during accumulation.** Models, feature construction, hyperparameters, atmospheric column list, decision criteria, location set, regime assignments, training set, and the comparison criterion MUST NOT be modified between v4-baseline lock and v4-baseline result commit. Operational fixes are permitted but MUST be disclosed.

**Concurrency with v4.** v4-baseline runs in parallel with v4. The two evaluations share infrastructure but have independent locks, accumulation windows, model artifacts, and result documents. No transfer of predictions or training between v4 and v4-baseline is permitted. Their independence is required for the comparison in Section 7 to be informative.

---

## 9. Provenance

**Lock commit:** TBD.

**Training set SHA-256:** `2263e038f7fca8bf4d0095e3ffc73f666963960260b0a6c635cae9c699fce14f`

**Companion pre-registration:** `pre-registration-v4`, locked at commit `01c35ba`, file `docs/PRE_REGISTRATION_v4.md`.

**Conformance:** This evaluation's evidence preservation conforms to the AEPF v0.1 Working Draft.

---

*End of pre-registration-v4-baseline-v2. Status: Draft pending lock commit.*