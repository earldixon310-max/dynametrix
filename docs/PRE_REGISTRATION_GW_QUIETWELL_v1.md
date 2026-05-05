# SpinPhase GW150914 Quiet-Well Test — Pre-Registration v1

**Version:** v1.0
**Identifier:** `spinphase-gw-quietwell-v1`
**Lock date:** 2026-05-04
**Author:** Earl Dixon
**Status:** Locked. Any change to the items below constitutes a methodology version bump and requires a new pre-registration document.

---

## 1. Purpose

This document fixes, in advance of computation, the methodology by which a follow-up "quiet-well" hypothesis will be tested against the same SpinPhase pipeline and segment population used in `spinphase-gw-blind-v1`. The test answers a question that v1 did not: not whether GW150914's coherence stands out *between segments*, but whether it stands out *within its own segment* relative to other times in the same 32-second window.

This is a strictly weaker claim than v1's. v1 tested whether the framework's overall coherence statistic ranks GW150914 above 99 PSD-matched background segments globally. v1 was falsified at R = 52 of 100 (`docs/RESULT_GW_v1_2026-05-04.md`). The quiet-well test asks whether the framework instead detects a *localized* coherence elevation within the GW150914 segment relative to the same segment's baseline behavior at other times — a within-system differential rather than a between-system contrast.

This test is registered explicitly *after* v1's outcome was observed, on the same blinded population. The integrity of the test rests on locking the methodology and the analysis code in git *before* any quiet-well differential statistic is computed for any segment.

---

## 2. The Test

For each of the 100 segments in the v1 blinded population (`analysis/spinphase_gw_blind/segments_blinded.csv`, locked at git commit `5082a58`), the SpinPhase phase-coherence statistic is computed at one TARGET anchor (the segment midpoint, matching v1) plus K = 10 BASELINE anchors at fixed offsets within the same segment. A within-segment differential D is computed per segment as a z-score of the target against the baseline distribution. The 100 D values are ranked descending; the rank R_D of the GW150914 segment is the primary outcome.

The GW150914 segment's identity within the population is already known (revealed by v1 unblinding under `unblind_and_rank.py`, sealed-key SHA `51b5b70b…`). The methodology lock therefore protects against post-hoc parameter tuning rather than against analyst foreknowledge of segment identity.

---

## 3. Methodology Inherited from v1

The following are inherited unchanged from `PRE_REGISTRATION_GW_v1.md`:

- Segment population: the 100 blinded segments under git commit `5082a58`.
- Strain access: GWOSC open data, H1 and L1, sample rate 4096 Hz.
- Whitening: gwpy `TimeSeries.whiten` with Hann window, 4-second FFT length, 50% overlap (per v1 Section 4.1).
- STFT: 0.25-second Hann window, 87.5% overlap, 4 Hz frequency resolution (per v1 Section 4.2).
- Chirp-track shape: exponential frequency interpolation between (offset = −0.40 s, 35 Hz) and (offset = +0.05 s, 220 Hz), per v1 Section 4.3. The track shape is fixed; only its anchor point within the segment varies.
- Δt search: ±10 ms in 0.5 ms steps, frequency-domain phase-rotation implementation per v1 Section 13 addendum.
- Phase-coherence statistic S: the maximum-over-Δt phase coherence summed at STFT-bin cadence along the chirp track, identical to v1 Section 4.4.
- Pipeline code: `analysis/spinphase_gw_blind/spinphase_pipeline.py` at git commit `335ce7b`. Frozen and not modified for this test.

---

## 4. Methodology New to Quiet-Well

### 4.1 Anchor positions

The chirp-track shape is anchored at K + 1 = 11 distinct time positions within each 32-second segment:

- **TARGET anchor:** t_anchor = segment_midpoint (= 16.0 s in segment-relative time). This is the v1 anchor.
- **BASELINE anchors (K = 10):** fixed offsets from segment start at:
  ```
  t_anchor ∈ {2.0, 5.0, 8.0, 11.0, 14.0, 18.0, 21.0, 24.0, 27.0, 30.0} seconds
  ```
  Equivalently, in midpoint-relative offsets: {−14, −11, −8, −5, −2, +2, +5, +8, +11, +14} seconds.

The baseline anchors are symmetric around the target (5 before, 5 after), spaced 3 seconds apart (no overlap of the 0.45-second chirp tracks with each other), and at least 2 seconds from the target (no overlap with TARGET). The most extreme baselines sit ≥ 2 seconds from the segment edges, providing margin against gwpy whitening boundary effects (which crop ~1 second from each end). Anchor positions are predetermined in this document, not selected per segment.

### 4.2 Coherence statistic per anchor

For each segment and each anchor t_anchor, the SpinPhase pipeline's phase coherence is computed exactly as in v1, with the chirp track anchored at t_anchor instead of at segment_midpoint. The output is a scalar S(t_anchor):

```
S(t_anchor) = max over Δt ∈ [-10, +10] ms of C_φ(Δt; t_anchor)
```

where C_φ is the phase-coherence statistic defined in v1 Section 4.4, with the chirp-track anchor shifted to t_anchor.

### 4.3 Within-segment differential statistic

Per segment, define:

```
S_target = S(segment_midpoint)
S_baseline[i] = S(t_anchor[i])  for i = 1 … 10

D = (S_target - mean(S_baseline)) / (std(S_baseline) + ε)
```

with ε = 1e-8 to prevent division by zero. std uses sample standard deviation (ddof=1).

D is a per-segment z-score: how unusual is the target window's coherence within the same segment, measured against that segment's own baseline distribution? D > 0 means the target window has higher coherence than the segment's baseline.

### 4.4 Directional prediction

The quiet-well hypothesis predicts D > 0 specifically for the GW150914 segment, because the chirp track happens to align with a real gravitational-wave signal at that anchor. For background segments, the target anchor is just another arbitrary 0.45-second window, so D should fluctuate around 0 with no preferred sign.

The test is therefore registered as **one-tailed**: D large in the *positive* direction is the registered prediction. D large in the negative direction would not constitute support for the quiet-well hypothesis.

---

## 5. Multiple Comparisons

- **Within-segment:** the 11 anchor positions per segment are predetermined and identical for all segments. No per-segment anchor selection. No multiple-comparison correction is needed within the differential statistic D itself.
- **Between segments:** D is computed identically for all 100 segments. The primary outcome is the rank R_D of the GW150914 segment among 100 D values sorted descending. As in v1, the rank framework already encodes the multiple-comparison structure; no additional correction is applied.

---

## 6. Primary Scalar Metric and Decision Criteria

### 6.1 Primary metric

R_D = rank of the GW150914 segment's D value within the 100-segment population, sorted by D descending (1 = highest D, 100 = lowest D).

### 6.2 Pre-registered decision criteria

| Outcome | Interpretation |
|---|---|
| R_D = 1 | **Strong claim.** SpinPhase's coherence statistic shows a within-segment elevation at the GW150914 event time greater than at any other segment's target window. Suggests the framework registers a localized coherence emergence at the event location even though it does not detect the event globally. |
| 2 ≤ R_D ≤ 5 | **Interesting.** GW150914's within-segment differential is in the top 5%. Worth follow-up testing on additional GW events (GW151012, GW151226). |
| 6 ≤ R_D ≤ 10 | **Suggestive.** Top 10%. Documented and reported. |
| R_D ≥ 11 | **No local emergence under this test.** SpinPhase's coherence statistic does not register a within-segment elevation at the GW150914 event location any more than at random target windows in random segments. The quiet-well hypothesis as registered is falsified for v1's pipeline configuration. |

### 6.3 Reporting

The full vector of 100 D values is reported, alongside the per-anchor S values for the GW150914 segment specifically (so that a reader can see the within-segment distribution that produced D). Auxiliary statistics (S_target, mean(S_baseline), std(S_baseline) for all 100 segments) are reported but do not alter the primary outcome.

---

## 7. Sanity Checks (auxiliary, not part of the primary outcome)

The following are reported alongside the rank result:

### 7.1 Unnormalized differential

D_simple = S_target − mean(S_baseline), without z-score normalization. Reported per segment. Allows comparison against the normalized statistic and provides a sanity check that the std normalization is not creating artifacts.

### 7.2 Per-anchor S distribution at GW150914

The 11 individual S values (target plus 10 baselines) for the GW150914 segment are reported in a table. This is the within-segment "footprint" of the framework's coherence response and is the most direct visualization of whether the quiet-well structure is present.

### 7.3 Background null shape

Histogram of D values across the 99 background segments, reported with mean and standard deviation. Used to characterize the background null distribution; any heavy upper tail in this distribution would inform interpretation of borderline R_D outcomes.

---

## 8. What This Test Does Not Claim

Registering this test makes none of the following claims:

- That a positive R_D ≤ 10 outcome validates SpinPhase as a GW detector. The test is on a single known event location and does not test forecasting or detection of unknown events.
- That the test generalizes to other GW events without explicit replication. A v2 quiet-well test would be required for GW151012 or GW151226.
- That a positive outcome rescues v1's primary claim. The between-segment ranking remains R = 52; the quiet-well differential measures something different.
- That the within-segment differential framework is privileged among possible reformulations. Other within-segment differentials (cross-correlation, variance, mutual information) might give different results; this test addresses only the SpinPhase phase-coherence formulation.

---

## 9. Relationship to v1

v1 (`spinphase-gw-blind-v1`) tests the between-segment ranking under the SpinPhase pipeline. v1 is locked and falsified.

This test (`spinphase-gw-quietwell-v1`) tests a within-segment differential under the same pipeline. It uses v1's locked segment population and pipeline code, but asks a different question and uses a different statistic.

The two tests are independent in the sense that:

- v1's R = 52 outcome does not constrain R_D in either direction.
- A positive R_D ≤ 10 outcome here does not invalidate or rescue v1's R = 52 outcome.
- A negative R_D ≥ 11 outcome here would tighten the cumulative evidence against the framework's coherence formulation, but would not retroactively change v1's locked record.

This sub-test does not modify v1's pre-registration, its result document, or its locked artifacts.

---

## 10. Test Logistics

### 10.1 Pre-test artifacts (committed before computing any D values)

The following are committed to git before any D value is computed:

- This pre-registration document.
- The analysis script `analysis/spinphase_gw_blind/quietwell_analysis.py` implementing exactly Sections 4.1–4.3 above. The script reads `segments_blinded.csv`, computes S at all 11 anchors per segment, computes D per segment, ranks all 100 D values descending, identifies the GW150914 segment from the (already-revealed) sealed key file, and writes a result CSV.

The lock for this test is the commit hash containing both this document and the analysis script. After that commit, the script must not be modified before D values are observed.

### 10.2 Test execution

The analysis script is run once. All 100 D values are computed. The result CSV (`quietwell_scores.csv`) is written and committed before any inspection of the rank R_D or the D distribution.

### 10.3 Result reporting

After commit, the rank R_D is computed and the outcome is classified per Section 6.2. A locked result document `RESULT_GW_QUIETWELL_v1_<date>.md` is written containing the full reported statistics and the outcome classification.

---

## 11. Lock and Provenance

This document is committed before the analysis script is written, or alongside it. The git commit hash for this document and the analysis script will be recorded in the result document.

The methodology, parameters (K = 10, baseline anchor offsets, statistic form D, decision criteria), and analysis script are fully bound at the lock commit. No parameter, threshold, or definition above may be modified before reporting the outcome.

---

## 12. Pre-Test Status (as of lock date)

At lock, the following work has been completed and is recorded as historical context (not part of the v1 quiet-well test):

- v1 blind test (`spinphase-gw-blind-v1`): outcome R = 52 of 100, "no detection capability under this test." Locked at `docs/RESULT_GW_v1_2026-05-04.md`.
- Confirmed: GW150914 blinded ID = `2cdc1b70-7106-4cd3-bc61-2bcb5576d4ea` (from sealed key, revealed at v1 unblinding).
- Sealed key SHA `51b5b70b…` verified at v1 unblinding.
- The analyst now has knowledge of which blinded ID corresponds to GW150914. This test's integrity rests on methodology and code being committed before D values are observed; analyst foreknowledge of segment identity is assumed and explicitly accommodated.

---

*End of Quiet-Well Test v1 Pre-Registration.*