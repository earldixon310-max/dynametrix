# Pre-registration v4 — Regime generalization test for calibrator-v3.0 across Great Plains and Ohio Valley severe-weather corridors

**Status:** Draft pending lock commit.
**Identifier:** `pre-registration-v4`
**Date:** 2026-05-17.
**Author:** Earl Dixon.

---

## 1. Hypothesis

The calibrator-v3.0 model produces probabilistic predictions of severe weather (severe wind ≥ 58 mph gusts, hail ≥ 1 inch diameter, tornado of any rating) whose calibration is regime-general rather than regime-specific.

This hypothesis is tested by evaluating the model independently across two structurally distinct severe-weather regimes that exercise different aspects of atmospheric organization:

**Organized-convection regime — Great Plains.** Locations: Wichita KS, Omaha NE, Dodge City KS. This regime is characterized by supercell evolution, dryline-driven organization, CAPE/shear-driven mesoscale coherence, and morphologically traceable tornadogenesis. Convective initiation tends to be discrete and evolutionarily well-defined; events that occur are typically the product of organized, identifiable atmospheric structures.

**Disorganized-convection regime — Ohio Valley / Mid-South.** Locations: Nashville TN, Louisville KY, Cincinnati OH. This regime is dominated by QLCS evolution, nocturnal severe systems, embedded tornadic circulations, and messy-mode convection. Convective organization is comparatively chaotic; substantial severe-weather signal comes from circulations embedded within linear or bowing structures rather than from discrete cells. Verification density is also elevated by population.

If the model's calibration mechanism tracks the evolution of atmospheric organization toward impact capability — independent of the morphological character of that organization — then the model should satisfy the calibration and skill criteria (Section 5) **independently in both regimes**. A model that succeeds in only one regime, or in neither, fails the regime-generalization hypothesis.

The hypothesis is supported if both regimes independently meet the per-regime criteria in Section 5. Mixed and negative outcomes are classified per Section 6.

---

## 2. System under evaluation

**Model:** `calibrator-v3.0` (the default `model_versions` entry as of v3's lock commit; unchanged).

**Feature builder:** `feature_builder_v3.py` (frozen at v3's lock commit; unchanged).

**Pipeline:** Hourly atmospheric ingestion (Open-Meteo `gfs_seamless`) → feature construction → model inference → calibrated output write → daily SPC ingestion → verification scoring against ground-truth events within ±50 km of each location and a 0–48 hour lead window.

v4 introduces **no modifications to v3's model, feature builder, scoring code, decision threshold, or matching radius.** v4 differs from v3 only in (a) the location set and (b) the regime-differentiation analysis structure. The underlying model is the same artifact under test in both pre-registrations.

---

## 3. Test data

**Atmospheric inputs:** Open-Meteo `gfs_seamless` API, fetched hourly per location.

**Ground truth:** NWS Storm Prediction Center daily storm reports, ingested daily at 14:00 UTC. Event types: severe wind (≥ 58 mph gusts), hail (≥ 1 inch diameter), tornado (any rating).

**Locations covered by v4 (6 total, all new registrations):**

*Great Plains regime — organized convection:*

1. Wichita, KS — `29172590-f05d-483c-b213-b851421e47ff` — 37.6872°N, -97.3301°W
2. Omaha, NE — `96ffa380-69ff-472e-9418-d981e695cf81` — 41.2565°N, -95.9345°W
3. Dodge City, KS — `7e37c63e-4cc2-4ea7-a539-c50fea99f683` — 37.7528°N, -100.0171°W

*Ohio Valley / Mid-South regime — disorganized convection:*

4. Nashville, TN — `d76fc5a1-e2b9-4662-89b4-1b1499ff3201` — 36.1627°N, -86.7816°W
5. Louisville, KY — `a26d4e34-4baf-463b-af98-1d28c54e3b9d` — 38.2527°N, -85.7585°W
6. Cincinnati, OH — `3885e98e-966c-48f3-86af-d4386cbc6cb1` — 39.1031°N, -84.5120°W

The UUIDs above are the canonical location identifiers under which v4's predictions, atmospheric observations, and verification outcomes accumulate. These identifiers were assigned at location registration immediately prior to the lock commit and are bound by this pre-registration.

**Existing locations operating under prior pre-registrations are not part of v4.** v3 continues to cover its original six-location set (which includes Norman OK as a Great Plains data point) under v3's own lock, accumulation window, and decision criteria. v4's analysis is restricted to the six new locations listed above. No predictions from existing locations contribute to v4's outcome.

**Accumulation window:** v4's analysis covers predictions produced between v4's lock commit (TBD) and v4's result document commit (TBD). Predictions produced before v4's lock do not count toward v4's outcome. All six v4 locations begin accumulating fresh from the lock commit.

**Sample-size threshold for outcome lock:** The result document binds at 90 days elapsed from the lock commit. No early-exit on sample size is permitted; the full window must elapse to ensure the analysis covers the peak of the severe-weather season (June–August in the monitored regions). Intermediate progress reports MAY be published during the window per Section 7.

---

## 4. Methodology

**Prediction.** For each location, every hour, the pipeline produces a calibrated probability that at least one qualifying severe weather event will occur within 50 km of the location within the next 0–48 hours.

**Verification matching.** Each calibrated output is scored against ground-truth events as follows:

- A prediction made at time T is matched against any qualifying SPC event with `event_at` between T and T + 48 hours.
- Geographic match requires haversine distance ≤ 50 km between location coordinates and event coordinates.
- If at least one qualifying event is matched, the outcome is recorded as `event_observed = True`; otherwise `event_observed = False`.

**Per-regime pooling and binning.** Verified predictions are partitioned by regime (Plains: locations 1–3; Ohio Valley: locations 4–6) and analyzed separately. Within each regime:

- Predictions are pooled across the three locations in that regime.
- Predictions are assigned to bins by predicted probability using 10 equal-width bins on the unit interval ([0, 0.1), [0.1, 0.2), …, [0.9, 1.0]).
- Bins with fewer than 30 predictions are excluded from the reliability evaluation and reported as excluded in the per-regime result section.

**Per-bin Wilson interval.** For each included bin in each regime, the observed positive-class frequency is compared to a Wilson 95% confidence interval constructed around the bin's mean predicted probability. The bin passes if the observed frequency falls within the interval.

**Per-regime Brier skill score.** BSS is computed separately for each regime as 1 − (Brier_model / Brier_climatology), where Brier_climatology is the Brier score of always predicting the per-location base rate over the accumulation window. Per-regime BSS uses only the predictions and outcomes from that regime's three locations.

**No cross-regime pooling.** Predictions from one regime are not combined with predictions from the other for any analytical purpose. The regime-generalization hypothesis requires that each regime be evaluated as an independent test.

---

## 5. Decision criteria

Per-regime criteria. For each of the two regimes (Plains, Ohio Valley) the following criteria are evaluated independently:

(a) **Reliability:** at least 6 of the populated bins (n ≥ 30) must pass the Wilson criterion as defined in Section 4.

(b) **Skill:** the per-regime Brier skill score must be positive (BSS > 0).

A regime is recorded as "calibrated and skilled" if both (a) and (b) hold for that regime.

**Hypothesis-level decision.** The regime-generalization hypothesis is supported if BOTH regimes are calibrated and skilled. It is refuted otherwise.

---

## 6. Outcome classification

| Plains regime | Ohio Valley regime | Outcome |
|---|---|---|
| Calibrated and skilled | Calibrated and skilled | **REGIME-GENERAL** — calibration validated across organized and disorganized severe-weather regimes |
| Calibrated and skilled | Not calibrated or not skilled | **PLAINS-ONLY** — model captures organized-convection structure but fails on disorganized convection |
| Not calibrated or not skilled | Calibrated and skilled | **OHIO VALLEY ONLY** — model captures disorganized-convection structure but fails on organized convection |
| Not calibrated or not skilled | Not calibrated or not skilled | **NEITHER** — model does not generalize at this expanded location set |

Within each regime, the result document also records the finer-grained per-criterion status (calibrated but no skill, skilled but miscalibrated, both pass, both fail) for diagnostic purposes. The four-cell classification above is the headline outcome.

Outcomes are recorded irrespective of which is favorable to the model. The result document records the exact outcome under the above classification, including all cases where the outcome is unfavorable.

---

## 7. Operational notes

**Pipeline integrity.** The pipeline runs continuously between v4's lock and v4's result commit. Outages, dormancies, or other interruptions that result in missing prediction-outcome pairs MUST be disclosed in the result document's implementation observations, with the duration and approximate scope of the gap and an assessment of any disproportionate effect on one regime versus the other.

**Pipeline modifications during accumulation.** The model, feature builder, scoring code, matching radius, lead window, decision criteria, location set, and regime assignments MUST NOT be modified between v4's lock and v4's result commit. Operational fixes (dependency updates, ingestion robustness improvements, infrastructure changes) that do not alter methodology are permitted but MUST be disclosed.

**Intermediate progress.** Progress reports MAY be published as separate documents during the 90-day accumulation window. Such reports MUST NOT modify v4's analysis pipeline, decision criteria, or outcome classification, and MUST clearly note that they are progress reports rather than final outcomes. They MUST NOT trigger an early lock of the result document.

**Concurrency with v3.** v4 runs in parallel with v3. The two evaluations share infrastructure but have independent locks, accumulation windows, decision criteria, location sets, and result documents. No transfer or pooling between v3 and v4 is permitted. Norman OK remains exclusively in v3's location set; the three Great Plains locations in v4 are independent registrations.

**Regime asymmetry disclosure.** If at any point during the accumulation window the two regimes show materially different verified-pair counts (e.g., one regime has accumulated ≥ 50% more verified outcomes than the other due to differential event rates), this asymmetry MUST be noted in the result document, alongside an assessment of whether it affects the comparability of the per-regime conclusions.

---

## 8. Provenance

**Lock commit:** TBD.

**Conformance:** This evaluation's evidence preservation conforms to the AEPF v0.1 Working Draft.

---

*End of pre-registration-v4. Status: Draft pending lock commit.*