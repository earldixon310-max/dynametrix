# CONSIDERED BUT DEFERRED — Pre-Registration: Dynametrix v3 + NWS HRRR Combination Study (v0.1)

**Disposition:** This pre-registration draft was retired by the independence diagnostic verdict on 2026-05-25.

**Diagnostic:** `DIAGNOSTIC_DYNAMETRIX_HRRR_INDEPENDENCE_2026-05-25.md`

**Diagnostic verdict:** DO_NOT_PROCEED. Pearson correlation of residual errors between Dynametrix v3 and the provisional HRRR-derived predictor was 0.9839 (95% bootstrap CI [0.9816, 0.9860]), far above the 0.7 threshold of protocol §5. The structural-dependence prior held: both predictors respond to the same upstream atmospheric signals (CAPE, shear, helicity, updraft helicity), and combination provides no detectable room for incremental value beyond what either source already supplies.

**Per protocol §5 of `INDEPENDENCE_DIAGNOSTIC_PROTOCOL.md`:** this draft pre-registration is preserved as a "considered but deferred" artifact rather than advanced to cross-model review and lock. The next AEPF audit is directed at a different target.

**Operator notes for future revisiting:**

If the Dynametrix-HRRR combination question is reopened, the conditions under which a revisit would be informative are:

1. A meaningfully different HRRR-to-probability transformation is proposed (e.g., one calibrated to the SPC's published outlook probabilities rather than to a UH-track-density curve). The residual-correlation finding is robust to the choice of transformation only in the direction of demonstrating dependence; a transformation that produces materially independent residuals would invalidate the current verdict.
2. Dynametrix transitions to a feature set that no longer overlaps substantially with HRRR's input fields (i.e., a meaningfully different upstream signal). The current v3 ingests atmospheric variables that HRRR also consumes; v4-or-later with non-overlapping upstream signal would have structural room for combination value the current v3 lacks.
3. The combination target shifts from HRRR to a less-correlated reference (e.g., a longer-range ECMWF ensemble, a climatology baseline). The diagnostic was specific to Dynametrix-HRRR; "Dynametrix vs. some other reference" is a distinct study.

Absent one of these conditions, this draft should not be re-locked. The independence finding stands.

---

## Full draft pre-registration (preserved verbatim for the record)

# Pre-Registration: Dynametrix v3 + NWS HRRR Combination Study (v0.1 DRAFT)

**Status:** DRAFT — not yet under cross-model review. Not locked. Do not execute against verification data.

**Framework:** Avenridge Evaluation and Publication Framework (AEPF)

**Operator:** Earl Dixon, Avenridge Institute

**Date of draft:** 2026-05-25

**Intended lock tag (post-review):** `dynametrix-hrrr-combo-v1.0-lock`

---

## 1. Evaluation question

Does combining Dynametrix v3 calibrated severe-weather probabilities with NWS HRRR severe-weather probabilities produce a measurably better-calibrated and/or more decision-useful prediction than either source alone, for a defined set of locations and a fixed forecast horizon over a defined evaluation window?

The question is one of *incremental decision value*. Dynametrix v3 has been independently audited under the calibrator-v3.0 lock (commit reference: see materialization manifest). NWS HRRR is a publicly available, operationally mature reference forecast. The study asks whether the two sources, when combined under a pre-registered combination rule, produce outputs that improve on the better individual source by a statistically and operationally meaningful margin.

This is NOT a study of whether Dynametrix is "better than" HRRR. The reference forecast is, by design, the standing operational benchmark; the question is whether Dynametrix adds information.

## 2. Population

**Locations:** The set of Dynametrix-monitored locations active under calibrator-v3.0 as of the lock commit. The full location list, with latitude, longitude, and Dynametrix internal identifier, is recorded in the materialization manifest. Locations added after lock are excluded from the analysis even if they begin producing v3 outputs during the evaluation window.

**Forecast horizon:** 1-hour severe-weather probability, valid for the hour beginning at the forecast issue time. This horizon is chosen because (a) it is the shortest horizon both Dynametrix and HRRR produce at high frequency; (b) it is the horizon most directly relevant to operational warning-tier decisions; and (c) it minimizes the temporal mismatch between forecast issue and verification.

**Event categories:** Tornado, severe hail (≥ 1 inch diameter), severe convective wind (≥ 58 mph), as defined by NWS Storm Prediction Center storm reports. The three categories are evaluated jointly under the existing Dynametrix verification matcher.

**Evaluation window:** The convective-season window 2026-06-01 through 2026-10-31, inclusive. The window is fixed at lock time. Forecasts issued outside this window are excluded even if both Dynametrix and HRRR archives cover them.

**Minimum event threshold:** The analysis proceeds only if the evaluation window contains at least 50 verified severe-weather events across the location set. If the threshold is not met, the RESULT document reports the study as inconclusive due to insufficient power; it is not re-run on an extended window.

## 3. Data sources

**Dynametrix v3 outputs:** Calibrated severe-weather probabilities from the locked calibrator-v3.0 model, captured continuously through the evaluation window. The materialization manifest records the calibrator commit, the model version identifier, and the SHA-256 hash of the daily output archive.

**NWS HRRR forecasts:** Operational HRRR forecast archive for the matching forecast issue times and locations. Source: NOAA HRRR archive at the URL pinned in the materialization manifest. SHA-256 hash of each materialized HRRR field archive recorded in the manifest. The HRRR severe-weather probability is constructed from HRRR fields via a pre-specified deterministic transformation, recorded as a frozen Python function in the analysis script and committed at lock time.

**SPC storm reports:** Ground-truth verification data from the NWS Storm Prediction Center storm report archive, ingested via the existing Dynametrix `storm_reports.py` service. The ingestion code is committed at lock time and is not modified during execution.

**Materialization discipline:** All three sources are materialized to local project files before lock. Analysis code reads from the local materialized files, never from upstream sources. The materialization manifest is committed alongside the pre-registration.

## 4. Comparison conditions

Three forecast streams are constructed and verified:

- **C1 — HRRR alone:** the HRRR-derived severe-weather probability for each location and issue time.
- **C2 — Dynametrix alone:** the calibrator-v3.0 output for each location and issue time.
- **C3 — Combined:** the output of the primary combination rule (Section 5) applied to C1 and C2.

A small number of secondary combination rules (Section 5) generate additional C3' variants. These are reported as secondary deliverables with multiple-testing correction.

## 5. Combination rules

**Primary combination rule (P):** Simple arithmetic mean of probabilities.

> P(combined) = (P(HRRR) + P(Dynametrix)) / 2

This rule is chosen as primary because (a) it is the textbook reference combination; (b) it requires no held-out tuning window, eliminating a class of analytic freedom; (c) any improvement under simple averaging is a strong signal that the two sources contribute independent information.

**Secondary combination rules (S1, S2, S3):** Reported with Bonferroni correction across the three secondary rules.

- **S1 — Conditional substitution:** Use C2 when C1 ∈ [0.20, 0.60]; otherwise use C1. The interval bounds are locked at this draft and not modified during execution.
- **S2 — Weighted average with held-out weights:** Weights determined from a calibration window of 2025-06-01 through 2025-10-31 (the prior convective season), held out from the evaluation window. Weights are computed once before lock, recorded in the materialization manifest, and not modified during execution.
- **S3 — Logical OR with shared threshold:** Both C1 and C2 are thresholded at 0.30; the combined output fires if either threshold is exceeded. This rule is a deterministic decision rule rather than a probability rule and is verified against POD/FAR rather than against Brier score.

If the data turn out not to support any of S1, S2, or S3 (e.g., the calibration window for S2 contains insufficient events to estimate weights), the affected rule is dropped from the analysis with the drop documented in the RESULT. Substitution of a different secondary rule after lock is not permitted.

## 6. Observables and metrics

**Primary metric:** Brier Skill Score of C3 against C1.

> BSS(C3 vs C1) = 1 − [BS(C3) / BS(C1)]

Bootstrap 95% confidence interval via stratified resampling over events and non-events, B = 10,000 resamples, random seed `0xA22EE` recorded in the analysis script at lock.

**Secondary metrics:**

- BSS(C2 vs C1) — Dynametrix alone versus HRRR alone, for completeness.
- BSS(C3 vs C2) — combined versus Dynametrix alone.
- POD (probability of detection) at threshold 0.30 for each of C1, C2, C3.
- FAR (false alarm ratio) at threshold 0.30 for each of C1, C2, C3.
- HSS (Heidke skill score) at threshold 0.30 for each of C1, C2, C3.
- Reliability diagrams for each of C1, C2, C3 using the existing Dynametrix bin-and-Wilson-interval code.

**Optional cost-weighted metric:** Expected operational cost under the cost matrix `{miss: 10, false_alarm: 1, hit: 0, correct_rejection: 0}`. The cost matrix is operator-specified and is reported alongside but not as a primary verdict input. Sensitivity to the cost ratio (5×, 10×, 20×) is reported as a single sensitivity table.

## 7. Statistical procedures

**Confidence intervals:** Bootstrap 95% CI on all skill scores with the locked seed.

**Multiple-testing correction:** Bonferroni correction across the three secondary combination rules (S1, S2, S3). The primary rule (P) is not subject to multiple-testing correction.

**Wilson interval:** On POD, FAR, and per-bin reliability via the existing `verification.py` Wilson helper (tested and locked).

**Independence diagnostic:** Pearson correlation of residual errors (event minus predicted probability) between C1 and C2 over the evaluation window, reported as a single number with bootstrap CI. This is reported as context for interpreting the primary metric, not as a verdict input.

## 8. Decision rules

**POSITIVE:** BSS(C3 vs C1) > 0 under the primary combination rule (P), with bootstrap 95% CI strictly excluding zero.

**NULL:** Bootstrap 95% CI on BSS(C3 vs C1) under P includes zero.

**AMBIGUOUS:** P returns NULL but at least one of S1, S2, S3 returns BSS > 0 with Bonferroni-corrected bootstrap CI excluding zero.

**INCONCLUSIVE (insufficient power):** The evaluation window contains fewer than 50 verified severe-weather events across the location set. The RESULT reports this verdict without computing the primary metric on the (insufficient) data.

## 9. Required disclosures

- **Independence assumption.** Dynametrix v3 and HRRR both draw on overlapping upstream atmospheric data sources. The combination's upper bound on incremental value is set by the degree to which their residual errors are independent. The independence diagnostic in Section 7 reports the observed residual correlation; readers should interpret the primary metric in light of that diagnostic.
- **Forecast horizon choice.** The 1-hour horizon is operationally relevant but is not the only horizon at which either source produces forecasts. A study at a different horizon (6-hour, 24-hour) is a separately pre-registrable study with its own lock chain; the present pre-registration does not generalize to other horizons.
- **Combination-rule sensitivity.** The primary verdict depends on the choice of primary combination rule (simple average). The secondary rules' purpose is to bound this dependence; if the primary returns NULL and a secondary returns POSITIVE, the AMBIGUOUS verdict is the correct disposition, and the operational claim is narrower than "combination helps" — it is "combination helps under this specific rule."
- **Geographic and seasonal scope.** The location set is the active Dynametrix v3 monitored locations as of lock; the evaluation window is the 2026 convective season. Generalization beyond this scope is not supported by the present study.
- **Cost matrix.** The optional cost-weighted metric uses an operator-specified cost matrix. The cost ratio is not derived from any external decision-economic analysis and should be treated as illustrative rather than as a calibrated operational parameter.
- **HRRR field-to-probability transformation.** The deterministic function mapping HRRR fields to a severe-weather probability is committed at lock time. This function is a methodological choice; an alternative function could produce different C1 values and therefore different BSS. The present study does not survey the space of HRRR-to-probability transformations.

## 10. Publication commitment

The RESULT document for this study will be published under the same AEPF discipline as the ERSAF and transformer calibration audits, regardless of outcome direction. POSITIVE, NULL, AMBIGUOUS, and INCONCLUSIVE verdicts are all published with equal artifact discipline. The publication commitment is binding at lock; it cannot be retracted post-unblinding.

## 11. Materialization manifest entries (to be filled at lock)

- Dynametrix v3 daily output archive: path, SHA-256, model version, calibrator commit.
- HRRR forecast field archive per day in evaluation window: path, SHA-256, source URL.
- SPC storm report archive: path, SHA-256, ingestion code commit.
- HRRR-to-probability transformation function: file path, SHA-256, git commit.
- Analysis script (`dynametrix_hrrr_combo.py`): file path, SHA-256, git commit.
- S2 weight computation output: path, SHA-256, weight values.

## 12. Cross-model review record (to be filled before lock)

- Reviewer identifier:
- Review date:
- Numbered findings with severity classifications:
- Operator responses:
- Disposition (BLOCK / PASS):

## 13. Lock commit

To be created after Sections 11 and 12 are complete. Single commit containing this pre-registration, the cross-model review record, the materialization manifest, and the analysis script. Tag: `dynametrix-hrrr-combo-v1.0-lock`. Push to public remote before unblinding.
