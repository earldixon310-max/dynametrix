# SpinPhase GW150914 Blind Detection Test — Pre-Registration v1

**Version:** v1.0
**Identifier:** `spinphase-gw-blind-v1`
**Lock date:** 2026-05-02
**Author:** Earl Dixon
**Status:** Locked. Any change to the items below constitutes a methodology version bump and requires a new pre-registration document.

---

## 1. Purpose

This document fixes, in advance of running the test and observing its outcome, the methodology by which SpinPhase will be evaluated as a blind detector of the gravitational-wave event GW150914. The test answers a single question: when applied to a population of 100 candidate LIGO data segments — one of which contains GW150914 and 99 of which contain noise only — how does SpinPhase rank the GW150914 segment?

This is **not** a claim that SpinPhase is or will be a validated GW detection method. It is the registration of a falsifiable test that will produce one of three outcomes:

- The GW150914 segment ranks at or near the top of the population (suggestive of detection capability)
- The GW150914 segment ranks indistinguishably from background (no detection capability under this test)
- The result is intermediate, with implications that must be assessed against the registered decision criteria below

This pre-registration supersedes the post-event structural audit of GW150914 already conducted (see SpinPhase historical analysis notes). The post-event audit established that SpinPhase produces a measurable structural response on the known event window. The blind test asks whether that response is *specific* to event-bearing data or also produced by noise.

---

## 2. The Test

A population of 100 LIGO data segments will be assembled (see Section 3). One contains GW150914; the location of GW150914 within the population is concealed from the analyst until after scoring. Each segment is processed independently through the SpinPhase pipeline (Section 5). Each segment receives a single scalar score (Section 6). Segments are ranked by score, descending. The rank position of the GW150914 segment is the primary outcome of the test.

The analyst conducting the scoring **must not know** which segment contains the event during scoring. This is enforced by either:

(a) Having a second person assemble and label the segments, withholding the labels until scoring is complete, or
(b) Using a deterministic-but-blinded labeling scheme (e.g., scrambled UUIDs) that is unscrambled only after the per-segment scores have been recorded.

The unblinding occurs after all 100 scores are recorded. No scores may be modified after unblinding.

---

## 3. Data Source and Segment Selection

### 3.1 Source

LIGO Open Science Center (https://www.gw-openscience.org/), O1 observing run, Hanford (H1) and Livingston (L1) detectors. Strain data sampled at 4096 Hz.

### 3.2 The GW150914 segment

A 32-second window centered on the published event time of GW150914: 2015-09-14 09:50:45.4 UTC. Both H1 and L1 strain are required for the segment to be valid.

### 3.3 The 99 background segments

Background segments are drawn from the same observing run (O1) under the following constraints, all locked here:

- 32 seconds long, with both H1 and L1 strain available.
- Drawn from periods labeled by LIGO data quality flags as **science quality** (no CAT1, CAT2, or CAT3 vetoes during the window).
- At least 1 hour separation from any known GW event detection in the official LIGO catalogs.
- Selected at randomized GPS times across the available O1 science segments, with selection seed recorded.
- PSD characteristics within an acceptable similarity band of the GW150914 segment's PSD (defined as having mean PSD in the 30–250 Hz band within ±50% of the GW150914 segment's mean PSD over the same band). Segments outside this band are rejected and replaced.

The selection seed and the resulting 100 GPS start times will be recorded in a sidecar file at the time the population is assembled. That file is part of the test artifact and is not modifiable post-hoc.

---

## 4. Pipeline Specification

The SpinPhase pipeline is applied identically to all 100 segments. Per-segment processing:

### 4.1 Whitening

Each detector strain is whitened against a Welch-estimated PSD computed from the segment itself. PSD parameters: Hann window, length 4 seconds, 50% overlap.

### 4.2 Time-frequency decomposition

STFT of the whitened strain. Window length: 0.25 seconds. Overlap: 87.5%. Frequency resolution: 4 Hz.

### 4.3 Chirp-track sampling

A single fixed chirp-like frequency-versus-time path is applied to all 100 segments. Path anchors:

```
(t1, f1) = (segment_midpoint - 0.40 s, 35 Hz)
(t2, f2) = (segment_midpoint + 0.05 s, 220 Hz)
f(t) interpolates exponentially between (t1, f1) and (t2, f2).
```

The path is anchored to each segment's midpoint, not to any external reference. Because the chirp-track parameters are fixed across all segments, the test specifically evaluates SpinPhase's response to a GW150914-morphology chirp signal centered on the segment.

This is a deliberate methodological choice: it constrains the test to GW150914-like morphology, which limits generalization but eliminates multiple-comparison inflation from per-segment chirp-parameter searches. A future version (`spinphase-gw-blind-v2`) may parameterize over a chirp-track grid with appropriate trial-factor correction; v1 does not.

### 4.4 Cross-detector phase coherence

For each sampled point `(t_k, f_k)` along the chirp path:

```
X_H1(t_k, f_k) = STFT_{H1}(t_k, f_k)        complex
X_L1(t_k - Δt, f_k) = STFT_{L1}(t_k - Δt, f_k)  complex

Δφ_k(Δt) = arg(X_H1(t_k, f_k)) - arg(X_L1(t_k - Δt, f_k))
```

Phase coherence at a candidate detector time-delay `Δt`:

```
C_φ(Δt) = | (1/N) · Σ_k exp(i · Δφ_k(Δt)) |
```

`Δt` is searched over the range `[-10 ms, +10 ms]` in 0.5 ms steps (41 distinct trials). The maximum `C_φ` over this range is taken as the observed coherence:

```
M_obs = max over Δt of C_φ(Δt)
```

The light-travel time between H1 and L1 is approximately 10 ms; the search range covers the full physically possible delay. A multiple-comparison correction is applied (Section 6).

### 4.5 Null distribution

For each segment, the null distribution is constructed by repeating the coherence calculation under time-shifted H1/L1 alignment that breaks the astrophysical correlation. Specifically: shift L1 strain by `s` seconds, where `s` is drawn from the set `{±1, ±2, ±3, ..., ±25}` (50 distinct shifts). For each shift, recompute `M_obs(s)` per Section 4.4.

The null distribution `{M_obs(s) : s ∈ shifts}` has `n_null = 50` samples. Mean `μ_null` and standard deviation `σ_null` are recorded.

`n_null = 50` is selected as the v1 computationally bounded minimum. Results are interpreted on a rank basis (Section 6.2), not as precise p-value estimation. Formal p-value claims would require substantially more null trials; v1 makes none. A future v2 may expand to `n_null ≥ 500` for tighter null distribution characterization and formal significance testing alongside ranking.

---

## 5. Multiple Comparisons

The within-segment time-delay search over 41 distinct `Δt` values inflates the apparent significance of the maximum-coherence value. This is corrected by applying the same maximum-over-Δt search to each null trial (Section 4.5). All shifts and the on-source coherence are subject to the same maximization, so the null distribution and the observed value share the trial-factor inflation. No additional correction is applied.

The 100-segment ranking is itself a multiple-comparison framework. Because the test asks "where does GW150914 rank?" rather than "is GW150914 significant?", trial-factor correction across segments is not required for the primary outcome.

---

## 6. Primary Scalar Metric and Decision Criteria

### 6.1 Primary metric

For each segment, the primary scalar score is:

```
Z = (M_obs - μ_null) / (σ_null + ε)
```

where `M_obs` is the observed peak coherence (Section 4.4), `μ_null` and `σ_null` are the null distribution moments (Section 4.5), and `ε = 1e-8` to avoid division by zero.

This is the segment's standardized phase-coherence z-score above its own null distribution.

### 6.2 Ranking and decision

All 100 segments are ranked by `Z` descending. Let `R` be the rank position of the GW150914 segment (1 = top, 100 = bottom).

Pre-registered decision criteria:

| Outcome | Interpretation |
|---|---|
| R = 1 | **Strong claim.** SpinPhase ranks the event-bearing segment above all 99 noise controls. Suggests SpinPhase has GW150914-morphology detection capability under this protocol. Justifies follow-up testing on additional LIGO events. |
| 2 ≤ R ≤ 5 | **Interesting.** SpinPhase places the event in the top 5%. Worth follow-up but not a strong detection claim. Possible noise outliers in the population. |
| 6 ≤ R ≤ 10 | **Suggestive.** Not a detection claim, but the event ranks in the top 10%. Documented and reported; methodology revision considered. |
| R ≥ 11 | **No detection capability under this test.** SpinPhase does not, in this protocol, distinguish the GW150914 segment from background. Result published; v2 protocol may be designed if a clear methodological flaw is identified, but the v1 result remains historical. |

The outcome is determined by `R` alone. Auxiliary statistics (raw coherence values, p-values, etc.) are reported but do not alter the primary outcome classification.

### 6.3 Reporting

The full vector of 100 `Z` scores is reported alongside the rank result. The ranked list, the random seed used for background selection, the GPS times of all 100 segments, and the full per-segment intermediate values (`M_obs`, `μ_null`, `σ_null`, best `Δt` per segment) are published as the test artifact. This permits independent replication and audit.

---

## 7. Sanity Checks (auxiliary, not part of the primary outcome)

The following auxiliary tests will be reported alongside the rank result. They do not modify the primary outcome but provide additional information about the framework's behavior:

### 7.1 Wrong-waveform subtraction test

The published GW150914 numerical-relativity waveform is subtracted from the H1 and L1 strains in the GW150914 segment. The SpinPhase metric is recomputed on the residual. The drop `D_correct = (M_pre - M_post_correct) / M_pre` is reported.

For comparison, three "wrong-waveform" subtractions are performed on the same GW150914 segment, using waveform models for binary inspirals with deliberately incorrect parameters (e.g., far higher mass, far lower mass, electromagnetic-binary-like template). The resulting drops `D_wrong_1, D_wrong_2, D_wrong_3` are reported.

A meaningful wrong-waveform sanity check requires `D_correct >> max(D_wrong_i)`. If wrong waveforms produce drops similar to the correct waveform, the metric is not specific to GW150914-morphology signal.

### 7.2 Null-only control

The same pipeline is applied to 100 segments, all from background (no GW event included). The distribution of `Z` scores across this null-only population is reported. If the null-only distribution has a long upper tail, the GW150914 result needs to be evaluated against that tail rather than against a Gaussian null assumption.

---

## 8. What v1 Does Not Claim

Registering this test makes none of the following claims:

- That SpinPhase is a validated gravitational-wave detector.
- That SpinPhase generalizes to non-GW150914 morphology events (different masses, longer/shorter signals, eccentric or precessing binaries, unmodeled bursts).
- Detection capability beyond the specific chirp-morphology fixed in Section 4.3.
- That SpinPhase is competitive with matched-filter detection pipelines.
- Cross-domain applicability to non-gravitational-wave systems.

What v1 *does* register is the methodology by which a single, clean, blind question — "can SpinPhase, applied with this fixed configuration, rank GW150914 above 99 background segments?" — will be answered.

---

## 9. Conditions for v2

A `spinphase-gw-blind-v2` register and corresponding methodology document will be required when any of the following changes:

- The chirp-track parameterization (a chirp-track grid with multiple-comparison correction; or template-free morphology search; or multi-event generalization).
- The primary scalar metric (e.g., switching to post-subtraction drop, or to a different coherence statistic).
- The detector pair or run selection (adding Virgo, using O2/O3 events, etc.).
- The null trial protocol (more shifts, different shift ranges, or alternate null construction).
- The decision criteria (different rank thresholds, weighted metrics, etc.).

A v2 register does not invalidate v1 results. v1's rank outcome remains historical fact about that specific protocol.

---

## 10. Test Logistics

### 10.1 Pre-test artifacts (committed before scoring)

The following are committed to git, with cryptographic hashes recorded, *before* the per-segment scoring is performed:

- This pre-registration document
- The segment-selection script and its random seed
- The 100 GPS start times in **blinded form**: each segment is identified by an opaque blinded ID (e.g., a scrambled UUID generated from the random seed) with no attribute that reveals which segment contains the event. The committed file has the schema `(blinded_segment_id, H1_start_gps, L1_start_gps)` and nothing more.
- The SpinPhase pipeline code at the test version (frozen)

The mapping from blinded ID to "which segment is GW150914" is held in a separate **sealed key file** that is **not** committed until after the per-segment scoring is recorded. The sealed key is generated by the segment-selection script and stored in a location inaccessible to the analyst during scoring (e.g., a separate directory, a colleague's machine, or a sealed envelope). The blinding is broken — and the key file committed to git — only after the score vector for all 100 segments has been finalized and committed.

If the analyst conducting scoring is the same person who generated the segments, the integrity of the blinding depends on this person's discipline; for a methodologically stronger version, segment generation and scoring should be performed by different people. v1 acknowledges this as a limitation and documents which mode was used at test execution time.

### 10.2 Test execution

Per-segment scoring proceeds with the analyst blinded to which segment contains GW150914 (Section 2). All 100 `Z` scores are recorded.

### 10.3 Unblinding

After all scores are recorded and committed, the GW150914 segment's identity is revealed. Rank `R` is computed. Outcome is classified per Section 6.2. Result is recorded as the test outcome.

### 10.4 Reporting

Test outcome — including rank, full score vector, auxiliary checks, and any methodological notes — is published as a single document, irrespective of whether the result is favorable.

---

## 11. Lock and Provenance

This document was written on the lock date listed above and reflects the methodology committed at that date. Once the test artifacts (Section 10.1) are committed and the test is executed, the methodology is fully bound: no parameter, threshold, or definition above may be modified before reporting the outcome.

The git commit hash for this document and the test artifacts will be recorded in the test outcome report.

---

## 12. Pre-Test Status (as of lock date)

At lock, the following work has been completed and is recorded as historical context (not part of the v1 test):

- Post-event structural audit of GW150914 (the original SpinPhase analysis using H1/L1 whitened strain, chirp-track sampling, phase coherence, null/shift trials).
- Reported pre-event coherence: V_pre = 0.924
- Reported post-waveform-subtraction coherence: V_post_waveform = 0.803
- Reported drop: D ≈ 13.1%
- The number of null trials in the original audit was small; this v1 protocol expands to 50 trials per segment.

The post-event audit informed the design of this blind test but does not constitute its result. The blind test stands or falls on its own outcome under the registered protocol.

---

*End of Pre-Registration v1 — SpinPhase GW150914 Blind Detection Test.*