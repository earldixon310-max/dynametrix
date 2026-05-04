# Verification Sub-Test v3a — Broader Spatial Outcome

**Identifier:** `verification-v3a-spatial-100km`
**Status:** Locked. The decision criteria below cannot be altered after re-scoring runs.
**Author:** Earl Dixon
**Lock date:** 2026-05-04
**Tests:** Existing `calibrator-v2.0` predictions (the same population that produced the v2 verification record). Does not modify v2's existing reliability data.

---

## Scientific Question

> **Does the v2 framework's commitment_probability have predictive skill against severe weather occurring at a broader spatial scale (within 100 km of the prediction location), even though it lacked skill at the precise prediction point (within 50 km)?**

This question tests an alternative interpretation of v2's verification result. v2 demonstrated POD ≈ 7%, FAR ≈ 90% at a 50 km radius — failing as a point-specific severe weather predictor. The hypothesis under test in v3a is that v2 may instead be detecting *regional* atmospheric organization at a coarser spatial scale, and that this regional signal correlates with severe weather happening *somewhere in the broader region* even when it doesn't fire at the precise prediction point.

If v3a finds skill at 100 km that v2 lacked at 50 km, the v2 result is reinterpreted: the framework measures regional structure, not point-specific severity, and the v2 register's "no skill" finding is restricted to the 50 km outcome it specifically tested.

If v3a finds no skill at 100 km either, the regional-organization hypothesis is falsified, and v2's failure remains a result about the framework itself rather than the spatial scope of the test.

---

## Hypothesis Outcomes

Three pre-registered outcomes:

- **v3a Brier skill score positive against climatology AND against atmospheric logistic at 100 km** → hypothesis supported. Framework detects regional severe-weather organization. v2's 50 km failure is a spatial-resolution finding, not a framework-level one.
- **v3a positive against climatology but not against atmospheric logistic at 100 km** → mixed. Framework reproduces what's in the inputs but doesn't add value beyond a simpler model at the broader radius.
- **v3a no skill at 100 km** → hypothesis falsified. v2's failure is unlikely to be primarily about spatial scope; the framework's outputs do not encode predictive structure at any scale we've tested. v3 (richer inputs) becomes the clearly-justified next move.

---

## Methodology

### Inputs
- The set of all `calibrator-v2.0`-tagged CalibratedOutput rows whose lead-time windows have closed at evaluation time. (No new predictions are generated for v3a.)
- Existing `ground_truth_events` records from the SPC ingestion pipeline, with `event_type ∈ {tornado, hail, wind}`.

### Event label
For each prediction at location `L` with window `[T, T + lead_hours]`:
```
y = 1 if at least one SPC storm report occurred within 100 km of L
        and within [T, T + lead_hours];
    0 otherwise.
```
Spatial radius **100 km** is the only registered v3a parameter that differs from v2. All other parameters identical to v2.

### Verification windows
Primary 0–48 hours, secondary 0–24 hours. Identical to v2.

### Decision threshold
0.5. Identical to v2.

### Baselines
1. **Climatology at 100 km** — historical base rate of any-SPC-report-within-100km at each location.
2. **Persistence at 100 km** — yesterday's prediction equals today's.
3. **SPC outlook** — same as v2.
4. **Atmospheric logistic at 100 km** — logistic regression on raw atmospheric inputs (CAPE, dewpoint depression, wind shear proxy, pressure tendency) trained on data prior to the v3a evaluation period, scored against the 100 km outcome.

### Implementation method
The verification engine's existing `find_matching_events` function accepts a configurable `search_radius_km`. v3a re-runs the matching logic at 100 km **without persisting separate VerificationOutcome rows** (which would conflict with the existing unique constraint on `(calibrated_output_id, decision_threshold)`). Instead, results are computed via a one-shot SQL/Python aggregation script and reported.

A future v3a-followup may include a schema change to extend the unique constraint with `search_radius_km`, allowing both 50 km and 100 km outcomes to persist alongside each other. v3a as registered tests via in-memory aggregation only.

### Reported statistics
Same as v2: POD, FAR, CSI with Wilson 95% CI at threshold 0.5; Brier; Brier skill score against each baseline; reliability diagram with 10 bins; per-bin sample size.

---

## What v3a Does Not Claim

- That 100 km is the "right" radius for the framework's prediction target. It is an exploratory test of the regional-organization hypothesis.
- That 100 km is the only radius worth testing. v3a-2 (testing 150 km or 200 km) may be designed if v3a results are intermediate.
- That a positive v3a result implies the framework is operationally useful. Scientific support for the regional-organization hypothesis is distinct from utility for any specific decision context.
- Cross-domain applicability or general-purpose validation.

---

## Independence from v3 (Richer Inputs)

v3a tests a different hypothesis than v3 (which is locked under a separate document for richer atmospheric inputs at 50 km radius). v3a's outcome influences whether v3 implementation should proceed as planned or be reconsidered:

- If v3a confirms the regional-organization hypothesis, v3 may be reframed: the question becomes whether richer inputs improve broader-radius prediction further, rather than whether they finally produce point-specific skill.
- If v3a falsifies the regional-organization hypothesis, v3 proceeds as designed — testing whether v2's failure was due to insufficient inputs at the original 50 km target.

v3a's design lock does not modify v3's design lock. Both stand as registered.

---

## Lock and Provenance

This document was written on the lock date listed above. The git commit hash will be recorded after committing this document and the results that will follow. Critically, **the analysis script and parameters must be committed BEFORE the results are inspected**, so that the v3a reading is locked methodology rather than tuned outcome.

---

*End of Verification Sub-Test v3a Pre-Registration.*