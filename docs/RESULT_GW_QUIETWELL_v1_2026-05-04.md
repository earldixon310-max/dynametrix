# SpinPhase GW150914 Quiet-Well Test v1 — Outcome

**Test identifier:** `spinphase-gw-quietwell-v1`
**Pre-registration:** `docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md`
**Run date:** 2026-05-04
**Author:** Earl Dixon
**Status:** Locked outcome. Per pre-registration Section 11, this result document is bound and not subject to revision.

---

## Summary

The SpinPhase GW150914 quiet-well test ranked the GW150914 segment **50th out of 100** by the pre-registered within-segment differential statistic D. Per the locked decision criteria (Section 6.2), this falls in the **R_D ≥ 11** band: *"No local emergence under this test."*

The within-segment differential framing — designed to test whether the framework's coherence statistic registers a localized elevation at the GW150914 event time relative to the same segment's own baseline — was falsified. The framework does not detect the event as a locally unusual feature any more than it detected the event as a globally unusual feature in the v1 between-segment ranking.

The most direct measurement: D for the GW150914 segment is **−0.058**, with an unnormalized differential of **−0.0073**. The on-source phase coherence at the chirp-track-anchored target window equals the mean baseline coherence to within a few thousandths. The framework's coherence statistic registers no local feature at the gravitational-wave merger time.

---

## Outcome per Pre-Registered Decision Criteria

| Outcome | Interpretation |
|---|---|
| R_D = 1 | Strong claim. Within-segment elevation exceeds all 99 controls. |
| 2 ≤ R_D ≤ 5 | Interesting. Top 5%. |
| 6 ≤ R_D ≤ 10 | Suggestive. Top 10%. |
| **R_D ≥ 11** | **No local emergence under this test.** |

**Quiet-well v1 outcome:** R_D = 50. **No local emergence under this test.**

R_D = 50 is at the 50th percentile of the 100-segment D distribution. The result is unambiguous and not borderline. The hypothesis registered for quiet-well v1 is falsified.

---

## Result Detail

### GW150914 segment statistics

| Field | Value |
|---|---|
| Blinded segment ID | `2cdc1b70-7106-4cd3-bc61-2bcb5576d4ea` |
| H1 / L1 GPS start | 1126259446.4 |
| S_target (coherence at midpoint anchor) | 0.4422 |
| mean(S_baseline) (mean over 10 anchors) | 0.4495 |
| std(S_baseline) (sample stdev, ddof=1) | 0.1266 |
| **D_simple = S_target − mean(S_baseline)** | **−0.0073** |
| **D = D_simple / (std(S_baseline) + ε)** | **−0.0580** |

**Cross-test consistency check:** the S_target value (0.4422) matches the v1 M_obs value for the same segment exactly, confirming both tests compute the SpinPhase phase-coherence statistic identically at the segment midpoint. This sanity check confirms the quiet-well analysis is built on the locked v1 pipeline without modification.

**Most striking observation:** the on-source coherence is *0.0073 lower* than the segment's own baseline mean. Not just non-elevated — marginally below. The framework registers the gravitational-wave merger time as indistinguishable from arbitrarily-chosen anchor positions in the same 32 seconds of data.

### Top 10 segments by D descending

| Rank | Blinded ID (truncated) | D | S_target | μ_baseline | σ_baseline | Is GW150914? |
|---:|---|---:|---:|---:|---:|:---:|
| 1 | `57d1fdf0..` | +3.2423 | 0.7538 | 0.4094 | 0.1062 | — |
| 2 | `e7fbcb19..` | +3.0822 | 0.5967 | 0.4213 | 0.0569 | — |
| 3 | `e5fb71f5..` | +2.6088 | 0.6775 | 0.4229 | 0.0976 | — |
| 4 | `48bfc3c6..` | +2.5036 | 0.6191 | 0.4074 | 0.0846 | — |
| 5 | `a172d49b..` | +2.4346 | 0.6436 | 0.4181 | 0.0926 | — |
| 6 | `9044e82e..` | +2.2751 | 0.6412 | 0.4188 | 0.0978 | — |
| 7 | `8f122de2..` | +2.2501 | 0.6506 | 0.4271 | 0.0993 | — |
| 8 | `3b9ca3f4..` | +1.8037 | 0.5928 | 0.4293 | 0.0906 | — |
| 9 | `ddecf406..` | +1.7670 | 0.6145 | 0.4758 | 0.0785 | — |
| 10 | `da1db44e..` | +1.7651 | 0.5808 | 0.4311 | 0.0848 | — |

GW150914 is not in the top 10. Its rank is 50.

---

## Diagnostic Reading

The top of the D distribution looks like the upper tail of a noise process: D values tapering from +3.24 down through +1.76 across the top 10, with no evidence of a privileged signature at the gravitational-wave segment. The segments scoring highest are background segments where, by chance, the chirp-track anchor at the segment midpoint produced a coherence value unusually high relative to the segment's own baseline anchors. This is not surprising — over 100 segments × 11 anchor positions, it's expected that a few segments will have midpoint-anchor coherence values significantly above their own baseline distributions, purely from sampling.

The GW150914 segment behaves as if it is one of those segments where the midpoint anchor happened to produce a coherence value within typical baseline range, despite the presence of an actual gravitational-wave signal at that anchor. Whatever the chirp signal contributes to the H1/L1 phase coherence is, evidently, indistinguishable from what the same chirp track produces at random anchor positions in the same 32 seconds of noise.

This is a stronger negative finding than v1 alone could provide. v1 told us the framework doesn't rank GW150914 highly *globally*. Quiet-well tells us it doesn't even register the event as locally unusual *within the same data*. The two tests measure different things, and both come back negative.

---

## Comparison to v1

| Statistic | v1 between-segment | Quiet-well within-segment |
|---|---|---|
| GW150914 rank | R = 52 of 100 | R_D = 50 of 100 |
| GW150914 primary metric | Z = −0.1133 | D = −0.0580 |
| GW150914 on-source coherence | M_obs = 0.4422 | S_target = 0.4422 |
| Reference for normalization | mean of 50 cyclic L1 shifts | mean of 10 within-segment baseline anchors |
| Both register: | "no detection" | "no local emergence" |

The two tests use different normalizations of the same on-source S_target. Both place GW150914 near the middle of the 100-segment distribution. The quiet-well differential, which controls for between-segment variability by comparing each target to its own segment's baseline, does not produce a meaningfully different rank than the cross-detector null comparison of v1.

---

## What This Falsifies, and What It Does Not

### Falsified

- The quiet-well hypothesis as registered: that SpinPhase's phase-coherence statistic, evaluated at the GW150914 chirp-track anchor, exceeds the same statistic evaluated at fixed baseline anchors within the same segment, by an amount that ranks GW150914 among the top 10 of 100 segments.
- The conjecture that the framework registers the gravitational-wave signal as a localized feature even though it does not register it as a global one. Both formulations of "where might the framework still be detecting something" have now been falsified on the same data.

### Not Falsified

- That a different *within-segment* differential — using a different statistic (e.g., simple cross-correlation, coherence-time-resolved, or amplitude-and-phase rather than phase-only) — might give different results. This test addresses the SpinPhase phase-coherence formulation specifically.
- That the broader conceptual question of "structural coherence as emergent property" is exhausted. Other operationalizations remain possible. This test addresses one operationalization at one event.
- The Dynametrix weather pre-registrations (v1, v2, v3, v3a). Those concern a different framework configuration applied to atmospheric data.

### Cumulative implications

This is the second falsifying result on the SpinPhase formulation, after `spinphase-gw-blind-v1`. Together with the three falsifying results in the weather domain (`pre-registration-v1`, `v2`, `v3a`), the cumulative empirical record across both domains for the framework's specific coherence formulations is five-of-five falsifying outcomes. The outstanding live test is `pre-registration-v3` (richer atmospheric inputs, forward-only verification), which began accumulating predictions on 2026-05-04 and will not have a meaningful sample size until approximately 2026-05-18.

The stopping rule that should follow from this record is a question for the program author rather than this document, but the document records that the locked v1 quiet-well result is consistent with the locked v1 between-segment result and with the locked weather verification results: the operational framework as currently implemented does not produce outputs that track the physical phenomena it was claimed to detect.

---

## Lock and Provenance

| Item | Reference |
|---|---|
| Quiet-well pre-registration | `docs/PRE_REGISTRATION_GW_QUIETWELL_v1.md` |
| Pre-registration and analysis script lock commit | (recorded after committing) |
| v1 blinded population | `analysis/spinphase_gw_blind/segments_blinded.csv` (commit `5082a58`) |
| v1 frozen pipeline | `analysis/spinphase_gw_blind/spinphase_pipeline.py` (commit `335ce7b`) |
| Quiet-well analysis script | `analysis/spinphase_gw_blind/quietwell_analysis.py` |
| Quiet-well score vector | `analysis/spinphase_gw_blind/quietwell_scores.csv` (commit `da1985b`) |
| Quiet-well rank script | `analysis/spinphase_gw_blind/rank_quietwell.py` |
| GW150914 blinded ID (revealed under v1) | `2cdc1b70-7106-4cd3-bc61-2bcb5576d4ea` |
| Sealed key SHA-256 (verified at v1 unblinding) | `51b5b70b37c47eed7a44cbcd2de0fce1c78ecefa0fae9b87d3d1d45e9e621d06` |
| This result document commit | (recorded after committing) |

Per pre-registration Section 11, the methodology was bound at the lock commit before any D value was computed; per Section 10.3, the score vector was committed before the rank R_D was inspected; per the program's overall discipline, the test outcome is published irrespective of whether it is favorable.

---

*End of SpinPhase GW150914 Quiet-Well Test v1 Outcome.*