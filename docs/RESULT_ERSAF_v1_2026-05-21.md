# RESULT — Expansion Residual Structure Assessment Framework (ERSAF) v1

**Pre-registration:** `docs/PRE_REGISTRATION_ERSAF_v1.md`
**Lock commit:** `33d18a5` (tag `ersaf-v1.0-lock`)
**Run executed:** 2026-05-21
**Author:** Earl Dixon

---

## Headline verdict

**ERSAF VERDICT: NULL** under the §7.7 combined positive-verdict criterion (Bonferroni-FWER primary FWER procedure on the 2-of-4 cross-diagnostic combination rule).

The NULL is *not* a "no structure was found" result. Under ΛCDM, the wavelet diagnostic detected one corrected-significant coefficient at the Monte Carlo precision floor (p < 10⁻⁴), at scale 1.29 bins and bin position 5 (z ∈ [0.032, 0.038]). The secondary BH FDR procedure (§6.3) surfaces a coherent broader pattern: an oscillating residual at the lowest retained redshift bins — negative coefficients at position 3 (z ∈ [0.024, 0.027]) and positive coefficients at position 5 — detected across multiple adjacent small wavelet scales, **present in the BH-significant results of all three baselines** (ΛCDM 11 indices, wCDM and w₀wₐ CDM 10 indices each, with the same paired positions).

The locked Bonferroni-FWER procedure rejects all but one of these coefficients (under ΛCDM only); the BH-FDR procedure surfaces the broader pattern; the headline ERSAF verdict is NULL because the §7.7 combined criterion requires ≥ 2 of 4 diagnostic families firing under Bonferroni-FWER and only the wavelet family fires under any baseline.

Two distinct interpretive frames apply to this result. Both are recorded here; neither is stronger than the other given the locked methodology's scope.

**Frame 1 — §9.3 formal interpretation.** Pre-registration §9.3 explicitly anticipates the pattern of "ΛCDM fires but extensions absorb the structure" and permits the following claim: *"that the detected ΛCDM residual organization is consistent with smooth dark-energy evolution under wCDM or w₀wₐ CDM."* Strictly applying this language: the wavelet firing at index 66 clears the Bonferroni-FWER threshold under ΛCDM (p < 10⁻⁴) but its closest counterparts under the extensions fall just above the same threshold (closest wCDM p-value at the same flat index 66 ≈ 6 × 10⁻⁴; same for w₀wₐ CDM). The extensions do weaken the structure enough to cross the FWER threshold. §9.3 permits the formal "consistent with smooth dark-energy absorption" framing.

**Frame 2 — Location-based interpretation.** The firing is at z = 0.032–0.038 — among the lowest retained redshift bins, immediately above the §3.1 z > 0.01 cut. Pre-registration §3.1 explicitly disclosed: *"peculiar-velocity-correction model dependence in the z > 0.01 retained sample is partially but not fully captured in the published covariance."* The firing location is exactly where that pre-registered systematic blind spot lives. Smooth dark-energy parameterizations modify expansion history primarily at intermediate redshifts; at z ≈ 0.025–0.038, the difference between the three baseline cosmologies' predictions is small. The persistence of the BH-significant oscillating pattern in *all three* baselines — including wCDM and w₀wₐ CDM where dynamical dark energy is permitted — is *more consistent with* a low-z systematic that smooth dark-energy parameterizations don't operate on than with smooth-extension-absorbable cosmological structure. Per §9.2, ERSAF cannot rule observational systematics absent from the published covariance in or out as alternative explanations; the §3.1 disclosure of peculiar-velocity systematics remains the applicable cautionary note for the firing location.

The locked methodology's verdict is NULL. The locked methodology's permitted interpretation under §9.3 is "consistent with smooth dark-energy absorption." The data's location pattern is also consistent with the pre-registered peculiar-velocity systematic blind spot. ERSAF v1's locked discipline does not adjudicate between these two interpretations.

---

## Per-baseline firing table

**Primary (Bonferroni-FWER, §6.1):**

| Diagnostic | ΛCDM | wCDM | w₀wₐ CDM | Threshold |
|---|---|---|---|---|
| Wavelet (298 coefficients) | **1 / 298 [FIRES]** | 0 / 298 | 0 / 298 | p ≤ 1.68 × 10⁻⁴ |
| PELT (1 test) | 0 / 1 | 0 / 1 | 0 / 1 | p ≤ 0.05 |
| ACF (5 lags) | 0 / 5 | 0 / 5 | 0 / 5 | p ≤ 0.01 |
| BAO (12 observables) | 0 / 12 | 0 / 12 | 0 / 12 | p ≤ 4.17 × 10⁻³ |
| **Families firing** | **1** | **0** | **0** | — |
| **Bonferroni 2-of-4 verdict** | **NULL** | NULL | NULL | — |

**Secondary (BH FDR, §6.3 disclosure, q = 0.05):**

| Diagnostic | ΛCDM | wCDM | w₀wₐ CDM |
|---|---|---|---|
| Wavelet | **11 / 298 [FIRES]** | **10 / 298 [FIRES]** | **10 / 298 [FIRES]** |
| PELT | 0 / 1 | 0 / 1 | 0 / 1 |
| ACF | 0 / 5 | 0 / 5 | 0 / 5 |
| BAO | 0 / 12 | 0 / 12 | 0 / 12 |

The BH FDR secondary disclosure is not the primary verdict — per §6.3, ERSAF's headline verdict is the Bonferroni-FWER procedure. But the secondary result is worth disclosing prominently because it offers a more nuanced story than the binary Bonferroni-NULL: under FDR control at q = 0.05, the wavelet diagnostic fires in all three baselines, with strongly-overlapping significant indices (ΛCDM: [1, 3, 17, 19, 33, 35, 49, 51, 64, 66, 94]; wCDM and w₀wₐ CDM share [1, 3, 17, 19, 33, 35, 49, 51, 64, 66]). Pre-registration §6.3 acknowledges that BH's PRDS assumption for the wavelet's correlated coefficients is approximate rather than derived; even so, the BH-significant indices recur in adjacent pairs and across baselines in a pattern that the locked Bonferroni-FWER threshold conservatively rejects.

---

## The single Bonferroni-firing wavelet coefficient (ΛCDM)

The ΛCDM wavelet diagnostic's single Bonferroni-corrected-significant coefficient lives at flattened-outside-COI index 66. Its identity in the (scale, position) grid:

| Property | Value |
|---|---|
| Scale index | 4 of 32 (log-spaced over scale range 1–7 bins) |
| Scale value | 1.2854 bins |
| Position index | 5 of 20 |
| Position z-range | z ∈ [0.0321, 0.0384] |
| Observed coefficient | +6.036508 × 10⁻² |
| Mock null p-value | < 10⁻⁴ (at Monte Carlo precision floor, §5.5) |
| Bonferroni threshold | 1.68 × 10⁻⁴ (= 0.05 / 298) |

The observed p-value is reported as "p < 10⁻⁴" per pre-registration §5.5 — at 10,000 mocks the empirical-distribution tail estimate cannot resolve p-values below the floor. The locked methodology does not assign a specific probability below this floor; "p < 10⁻⁴" is the disclosure standard.

Under the BH FDR secondary procedure, this coefficient is among the 11 ΛCDM-significant indices. The same index 66 also appears in the BH-significant lists for both wCDM and w₀wₐ CDM, meaning the wavelet structure at this (scale, position) is *FDR-detectable in all three baselines* even though only ΛCDM clears the FWER-controlling Bonferroni threshold.

---

## Best-fit cosmologies per baseline

Documented for transparency and reproducibility. ERSAF does not test cosmological parameter preferences; these are the GLS-fit values that define the baseline cosmology under which residuals are computed. Marginalized M̂_B values are computed via the closed-form §3.1 formula at the converged best-fit and are diagnostic-only.

| Baseline | H₀ | Ω_m | w / w₀ | wₐ | M̂_B |
|---|---|---|---|---|---|
| ΛCDM | 65.069 | 0.3163 | (fixed: −1) | (fixed: 0) | −19.5071 |
| wCDM | 61.787 | 0.2956 | w = −0.8785 | (fixed: 0) | −19.6058 |
| w₀wₐ CDM | 64.485 | 0.3208 | w₀ = −0.7895 | wₐ = −0.9001 | −19.5043 |

**Note on the wCDM and w₀wₐ CDM fits.** Both extensions show substantial departures from ΛCDM-equivalent (w = −1 and (w₀, wₐ) = (−1, 0)). The w₀wₐ CDM fit's direction — w₀ > −1 with strongly negative wₐ — matches the dynamical-dark-energy direction reported by DESI 2024 VI (Adame et al. 2024 VI) as their headline result. ERSAF does *not* test the statistical significance of this departure or the Bayesian evidence ratio between baselines; that is out of scope per §8. The values are documented here because they define the baselines under which the residuals were computed.

---

## Location and structure of the detected signal

The complete tabulation of the 11 BH-FDR-significant wavelet coefficients under ΛCDM, mapped to (scale, position, redshift, observed value):

| Flat idx | Scale (bins) | Position | z-range | Observed coef |
|---|---|---|---|---|
| 1   | 1.000 | 3 | [0.024, 0.027] | −6.466 × 10⁻² |
| 3   | 1.000 | 5 | [0.032, 0.038] | +5.634 × 10⁻² |
| 17  | 1.065 | 3 | [0.024, 0.027] | −6.520 × 10⁻² |
| 19  | 1.065 | 5 | [0.032, 0.038] | +6.388 × 10⁻² |
| 33  | 1.134 | 3 | [0.024, 0.027] | −7.019 × 10⁻² |
| 35  | 1.134 | 5 | [0.032, 0.038] | +5.810 × 10⁻² |
| 49  | 1.207 | 3 | [0.024, 0.027] | −5.834 × 10⁻² |
| 51  | 1.207 | 5 | [0.032, 0.038] | +6.044 × 10⁻² |
| 64  | 1.285 | 3 | [0.024, 0.027] | −7.007 × 10⁻² |
| **66**  | **1.285** | **5** | **[0.032, 0.038]** | **+6.036 × 10⁻²** ← Bonferroni-firing under ΛCDM |
| 94  | 1.457 | 5 | [0.032, 0.038] | +5.821 × 10⁻² |

The pattern is structurally clear: an oscillating residual at the two lowest retained bin positions, detected across multiple adjacent small wavelet scales (1.000 → 1.457 bins). Negative deviation of ~7 × 10⁻² magnitude at z ≈ 0.025, positive deviation of ~6 × 10⁻² magnitude at z ≈ 0.035. The wavelet decomposition surfaces the same physical residual feature at six adjacent scales because that is what continuous wavelet transforms do for sharp localized features in the input signal.

**Under wCDM and w₀wₐ CDM**, the BH-FDR-significant indices reduce to the same 10 indices (positions 3 and 5 across the same scales 1.000–1.285 bins) but the Bonferroni-firing index 66 fails the FWER threshold under both extensions. The pattern's magnitude is slightly reduced but its structural identity (positions, scales, sign-alternation) is preserved across all three baselines.

**Connection to §3.1's pre-registered systematic disclosure.** The firing redshift range (z = 0.024 – 0.038) is the lowest two retained bins after the §3.1 `z > 0.01` cut. §3.1 explicitly notes the peculiar-velocity-correction systematic in this regime. The locked discipline does not allow ruling this systematic in or out, but the location is consistent with where pre-registration warned that residual organization should be interpreted with caution.

**Connection to §9.6's broad-feature blind spot.** The firing's small wavelet scale (1.0–1.5 bins) is exactly the scale range where the locked T&C 1998 e-folding COI gives the most testable coefficients. The discipline's diagnostic battery is most sensitive at exactly the scales where this feature appears, which is partly why it surfaces at all under the strict §6.1 Bonferroni correction. A complementary blind spot — broad smooth structure beyond scale 5 bins — was disclosed in §9.6 as untested by the locked methodology.

---

## Required §9.5 disclosures

**Monte Carlo precision floor.** N_MOCKS = 10,000 per baseline; the empirical-null p-value floor is 1 / N_MOCKS = 10⁻⁴. Per §5.5, p-values below this floor are reported as "p < 10⁻⁴" rather than as specific numerical values. The single Bonferroni-firing wavelet coefficient under ΛCDM is at this floor.

**Convergence failure rate.** **0 / 30,000 across all three baselines.** No mock fit failed to converge under any of ΛCDM, wCDM, or w₀wₐ CDM. The §5.4 1% pause-and-reconsider threshold was never approached.

**Eisenstein-Hu r_d approximation under w₀wₐ.** Per §7.4, r_d is computed via the Eisenstein & Hu 1998 fitting formula at every fit iteration, identically under all three baselines. The fitting formula assumes standard radiation-matter transition dynamics and is acknowledged as an approximation under w₀wₐ where dark-energy evolution could in principle perturb pre-recombination physics. Verification against CAMB/CLASS-based numerical r_d computations was not part of ERSAF v1.

**Paired-mock structure across baselines.** Per §7.5, mock realizations are paired across the three baselines: mock i under ΛCDM, wCDM, and w₀wₐ CDM shares the same Gaussian noise vector z_i. The mock observations differ only in their baseline-cosmology predictions. The three null distributions are therefore not statistically independent of one another; this is intentional and provides a cleaner comparison structure across baselines than independent mock generation would.

**2-of-4 combination rule (§6.5).** The combination rule does not strictly control any standard error-rate quantity. It is a pre-registered heuristic chosen to be more conservative than 1-of-4 single-diagnostic firing while not requiring full unanimity. The four diagnostics are not strictly independent — the wavelet and ACF are mathematically related, and all four operate on the same binned residual signal. The actual joint false-positive rate of the combination rule under the null is not analytically derivable. The rule's role is to guard against single-diagnostic artifacts.

**PELT count statistic power limitation on a 20-point signal (§4.3).** The change-point count statistic under BIC penalty on a 20-bin signal has limited discriminating power. The null distribution is concentrated at low integer values, and the test is informative primarily when observed structure produces substantially more change-points than chance. The observed PELT count under ΛCDM was 1; under wCDM and w₀wₐ CDM, 0. The null mock distribution for PELT counts produced a two-sided p-value of 1.0 for the ΛCDM observed count of 1 (i.e., the count of 1 was at or near the mode of the mock null distribution) and 0.92 / 0.98 for wCDM / w₀wₐ CDM respectively. The PELT diagnostic's contribution to the verdict was a confirmed-non-firing across all three baselines.

**Broad-feature insensitivity of the wavelet diagnostic on the locked 20-bin signal (§9.6).** Per the §4.2 amendment locking the Torrence & Compo 1998 e-folding COI criterion at `coi_width = ceil(scale × √2.5)`, wavelet scales above approximately 5 bins on a 20-bin signal have zero coefficients outside the COI. The diagnostic is structurally insensitive by construction to residual organization whose characteristic redshift extent exceeds approximately one-quarter of the signal length. The 298 testable wavelet coefficients are distributed across 28 of the locked 32 log-spaced scales in the 1–7 bin range. The 4 highest scales contributed zero testable coefficients and did not enter the Bonferroni denominator.

**ACF lag set is locked at 1–5 (§4.4).** Lag-1 through lag-5 autocorrelation was tested under all three baselines. None were significant under Bonferroni (threshold p ≤ 0.01). Per-lag observed p-values: ΛCDM [0.459, 0.671, 0.765, 0.165, 0.355]; wCDM [0.912, 0.103, 0.629, 0.330, 0.642]; w₀wₐ CDM [0.808, 0.067, 0.501, 0.470, 0.947]. The diagnostic is sensitive to linear lag-1-through-5 dependence under Gaussian-like residual assumptions; non-linear or higher-lag dependence is not constrained.

**BAO per-observable test (§4.5).** Twelve DESI DR1 BAO observables tested individually against their respective mock-null distributions. None significant under Bonferroni at p ≤ 4.17 × 10⁻³ under any baseline. **Descriptive note (not part of the verdict):** under ΛCDM, the LRG1 D_H/r_d (observable index 2, z = 0.510) and LRG2 D_M/r_d (observable index 3, z = 0.706) returned the lowest p-values among the 12 observables — p = 0.0112 and p = 0.0268 respectively. These two observables straddle the redshift region where DESI III §8.2 itself flagged a 2.5–3σ DESI-vs-SDSS BAO tension. The locked threshold of p ≤ 4.17 × 10⁻³ rejects both as significant; they are documented as descriptive observations only.

---

## Operational §10 fixes applied during execution

Three operational fixes were applied between the lock commit (`33d18a5`) and run completion. Per pre-registration §10:

> "Operational fixes (dependency updates, runtime environment configuration, OpenMP-conflict workarounds analogous to prior audits) that do not alter methodology are permitted but MUST be disclosed in the result document."

Each is disclosed below. None modified the analysis logic, the cost function, the penalty, the test statistic, or any methodological choice.

**Fix 1: `PYTHONIOENCODING=utf-8` environment variable set before Python invocation.** Windows PowerShell's default stdout codec (cp1252) cannot encode U+0302 (the combining circumflex used to render `M̂_B`). When Python's stdout is redirected through Tee-Object for logging, Python 3 on Windows falls back to the system codec rather than UTF-8. The fix was setting `$env:PYTHONIOENCODING = "utf-8"` in the PowerShell session before launching Python. Affects only console output encoding; analysis logic unchanged.

**Fix 2: `-u` flag added to Python invocation (`python -u ersaf_analysis.py ...`) for unbuffered stdout.** Python's default block-buffering on Windows when stdout is redirected suppresses progress output until the buffer fills (4–8 KB). With only ~70 print lines across the entire run, the buffer never fills organically and all output remained suppressed until process exit. The `-u` flag forces unbuffered stdout/stderr, allowing real-time progress monitoring and per-baseline timing capture. Equivalent to setting `PYTHONUNBUFFERED=1`. Affects only print-flush timing; analysis logic unchanged.

**Fix 3: `self.signal = signal` added to the custom `_WeightedGaussianMeanShiftCost` class's `fit()` method in `compute_pelt_change_count` (§4.3).** The locked custom PELT cost class stored residuals, variances, and prefix sums but did not store `self.signal` as required by `ruptures.detection.Pelt.predict()` for internal bookkeeping. The diagnostic raised an `AttributeError` the first time it was executed on real data during run mode. Fix: one line added — `self.signal = signal` — to comply with `ruptures.base.BaseCost`'s API expectation. The cost function (`S_rriv − S_riv²/S_iv`), the BIC penalty (`log(n)`), the minimum segment length (2), and the test statistic (change-point count) are *all unchanged*. The locked PELT methodology is preserved byte-for-byte; the fix enables the methodology to execute under ruptures' API. Fix committed at `552cc0c` (lock commit reference: `33d18a5`).

**Process observation noted for ERSAF v2 and future audits in this discipline.** This testing gap — that neither the interim cross-model review (#102) nor the comprehensive pre-lock cross-model review (#96) exercised the PELT diagnostic on real data — is a real process limitation in the verification gates as constituted for ERSAF v1. Future audits in this discipline should include a pre-lock smoke test that executes every locked diagnostic family on a representative input, in addition to the existing cross-model review structure. This is recorded as a discipline-pattern improvement and is not a methodology change to ERSAF v1.

---

## Interpretive constraints reaffirmed (§9.1–§9.4)

### What this NULL verdict establishes

- That under the specific methodology of ERSAF v1 — locked at commit `33d18a5`, pre-registered in `docs/PRE_REGISTRATION_ERSAF_v1.md` — on Pantheon+ (Brout et al. 2022, unanchored, post-z > 0.01 cut) combined with DESI DR1 BAO (Adame et al. 2024 III + IV, all twelve observables), no statistically significant non-smooth residual organization was detected via the §7.7 combined criteria (Bonferroni-FWER 2-of-4 diagnostic-family-firing under ΛCDM AND preservation under both wCDM and w₀wₐ CDM).
- In the specific firing pattern observed — wavelet fires 1 / 298 under ΛCDM, 0 / 298 under both extensions — that the detected ΛCDM residual organization is consistent with smooth dark-energy evolution under wCDM or w₀wₐ CDM (per §9.3).
- That the cumulative analysis places observational constraints on the existence of detectable non-smooth ΛCDM-deviation at the sensitivity of this specific test on these specific datasets.

### What this NULL verdict does NOT establish

- That ΛCDM is correct as a complete cosmological framework. Absence of detection is consistent with structure existing at sensitivity below the audit's noise floor; structure existing at redshift ranges or length scales where the diagnostic battery is insensitive; structure existing in forms (non-linear dependence, higher-order moments, anisotropies) the locked diagnostics do not probe; sample sizes too small for existing structure to reach corrected significance.
- That alternative cosmological models are ruled out. ERSAF tests against only two specific phenomenological extensions (wCDM, w₀wₐ CDM).
- That observational systematics do not drive the residuals. The audit treats the published Pantheon+ + DESI DR1 covariance matrices as accurate descriptions of measurement uncertainty; systematics absent from those covariances are not addressed.
- That future surveys would replicate the NULL. ERSAF is a single test on a single data combination at a single lock-commit dataset revision.
- **That the operator's prior conceptual program — including "coherence," "MCC/CI," "structural commitment," cyclic cosmology, or emergent spacetime — is refuted by this NULL.** Per §9.4 (binding interpretive constraint): "The audit measures residual structure in the locked datasets under the locked methodology; it does not test any theoretical framework. A NULL verdict provides no evidence for or against any framework that proposes mechanisms for the same observable. The framework-silent posture is symmetric across both verdict directions."
- That the dynamical-dark-energy preference reported by DESI 2024 VI is refuted. The wCDM and w₀wₐ CDM fits in this analysis show similar departures from ΛCDM-equivalent parameter values to DESI's headline result; ERSAF's §7.7 design specifically filters out *smooth-extension-absorbable* signal, which is the kind of signal DESI 2024 VI's analysis is configured to detect at the global-fit level. The locked-methodology NULL here is a downstream consequence of the §7.7 filter, not a statement about the cosmological-parameter-preference question that DESI 2024 VI addresses.

---

## What ERSAF v1 deliberately did not test

The locked scope of ERSAF v1 (§8, audit boundary) excludes several questions that are scientifically live in the joint Pantheon+ + DESI DR1 data combination. They are documented here so that the v1 scope is locked from both ends — what was tested and what was excluded.

**Out of scope for ERSAF v1, but candidate questions for separately-pre-registered follow-up audits in this discipline:**

- **Direct test of dynamical dark energy.** Is `(w₀, w_a) ≠ (−1, 0)` significant in the joint Pantheon+ + DESI DR1 data? ERSAF v1's §7.7 design explicitly filters this out as "smooth-extension-absorbable." The question is the live scientific finding from DESI 2024 VI. A separately-pre-registered ERSAF v2 (or distinctly-named follow-up audit) could ask this question under the same pre-registration + lock-commit + cross-model-review discipline pattern applied to ERSAF v1.

- **Targeted test of the low-z residual feature detected here.** The BH-FDR-significant oscillating pattern at z = 0.024–0.038 (positions 3 and 5, scales 1.0–1.5 bins) is a documented finding of ERSAF v1 but the locked methodology does not adjudicate between the "smooth-extension-absorbable" framing (§9.3) and the "low-z peculiar-velocity systematic" framing (§3.1 disclosed systematic + §9.2 inability to rule out). A targeted analysis with finer low-z binning, alternative peculiar-velocity-correction models (the Pantheon+ release ships several), and a `z > 0.05` sensitivity comparison would directly address whether the firing is systematic or residual cosmological structure. This is a smaller-scope follow-up than the dynamical-dark-energy audit and might be more methodologically informative as a discipline-pattern demonstration.

- **Global Bayesian evidence comparison among ΛCDM, wCDM, w₀wₐ CDM, and possibly more flexible parameterizations** (spline-based w(z), Gaussian-process residual w(z) models, etc.). ERSAF v1 tests residual organization conditional on a baseline; it does not compare baselines' Bayesian evidences. A direct evidence-ratio audit would address "what cosmology does this data prefer?" which is conceptually distinct from "are there residuals beyond a baseline?"

- **Targeted analysis of the LRG2 (z = 0.71) D_M/r_d vs. SDSS tension.** DESI III §8.2 itself flagged a 2.5–3σ tension between DESI's LRG2 D_M/r_d measurement and SDSS at the same effective redshift. ERSAF v1's BAO per-observable test treats each of the 12 observables under Bonferroni at α/12 ≈ 4.17 × 10⁻³, which is stringent enough that the LRG2 tension does not surface as significant; a dedicated targeted analysis with a different multi-test correction structure could ask the LRG2 question directly.

- **Anisotropies and sky-position dependence.** ERSAF v1 treats residuals as a one-dimensional function of redshift only. The locked binning collapses sky-position information. A 2D or 3D residual-structure analysis preserving sky position could probe anisotropic structure.

- **Broad smooth structures in the redshift dependence beyond the wavelet's scale range.** The locked wavelet COI under T&C 1998 e-folding renders scales above approximately 5 bins (z-extent of ~one-quarter of the signal) untestable. A different localized-decomposition method, a longer signal (larger SN compilation), or finer binning could probe the missing scale range.

- **Higher-order non-linear residual structure** beyond what linear ACF lag-1-through-5 and the locked wavelet basis can detect. Gaussian-process residual modeling, spectral coherence methods, or higher-order moment analyses are alternatives outside ERSAF v1's locked battery.

- **The Eisenstein-Hu r_d approximation under w₀wₐ.** ERSAF v1 uses EH 1998 identically under all three baselines; CAMB/CLASS numerical r_d would be more accurate under evolving dark energy. A separate analysis verifying that the EH approximation does not bias the present result, by re-running with CAMB-computed r_d, would close this acknowledged blind spot.

**No commitment is made here to running any of these audits.** They are documented as candidate questions to lock the v1 scope explicitly from both ends. The audit-trail discipline is preserved whether or not any follow-up is eventually pursued.

---

## Reproducibility and provenance

**Run execution.**
- Hardware: Windows host with NumPy BLAS multi-threaded per-mock linear-algebra operations (no explicit mock-loop parallelization in the locked `run_mocks_for_baseline` function).
- Total wall-clock: 4 hours 54 minutes (2514.7 + 5018.2 + 10121.5 seconds across the three baselines; the scaling reflects the parameter-count increase from 2 → 3 → 4 fit parameters and the corresponding optimizer cost per mock).
- Pre-registration §5.6 estimated ~2 hours on 8-core hardware assuming parallelization that the locked `run_mocks_for_baseline` does not implement (the per-mock refit loop is sequential; NumPy BLAS may parallelize per-mock linear-algebra operations). The §5.6 estimate is overoptimistic for the as-locked implementation and is disclosed here as an operational note.
- 0 convergence failures across all 30,000 mock fits.

**Output artifacts.**
- `analysis/ersaf/ersaf_results.json` — full structured result manifest including per-baseline p-value arrays, Bonferroni-FWER results, BH FDR results, best-fit parameters, M̂_B per baseline, convergence-failure rate per baseline.
- `analysis/ersaf/ersaf_LambdaCDM_arrays.npz` — per-baseline raw arrays: observed wavelet coefficients (32 × 20 grid), COI mask, wavelet scales, PELT count + locations, ACF values, BAO residuals, bin means, bin SEs, bin z-ranges, plus full mock distributions for all four diagnostics.
- `analysis/ersaf/ersaf_wCDM_arrays.npz` — same structure as ΛCDM arrays.
- `analysis/ersaf/ersaf_w0waCDM_arrays.npz` — same structure as ΛCDM arrays.
- `analysis/ersaf/run_log_20260521_141135.txt` — full execution log with timestamped progress prints.

**Output SHA-256s** (computed post-run; for inclusion in the lock commit's follow-up provenance record):
- `ersaf_results.json`: `FFBD7FDEA919CC31385206E712119CDB9AA867D44CB9882DDF65AB72EE883C9B`
- `ersaf_LambdaCDM_arrays.npz`: `6DE35F23D8FED09CF505781084890100EA52B5AEC438AA742C01D69DB1732DB5`
- `ersaf_wCDM_arrays.npz`: `F3376E58A427B015CAC4E899AE084B0300392367B4293615B10FA3EDA0500FD1`
- `ersaf_w0waCDM_arrays.npz`: `5588D6609B4091B85B4DFAB19D24E9AF69EED95BE1C1893EBDA7FAF473A6FBCF`

**Reproducibility statement.** The analysis is fully deterministic given the locked dataset versions, library versions, and seed `SeedSequence(150914).spawn(10000)`. Re-running `ersaf_analysis.py run` against the locked artifacts at commit `33d18a5` (with the three operational fixes disclosed above) reproduces numerically equivalent outputs within float-precision tolerance. The §10 "single execution" clause is honored: this run is the canonical execution of ERSAF v1; re-runs for reproducibility verification do not produce new outcome documents.

**Methodology pattern.** This audit followed the pre-registered methodology pattern documented in `docs/standards/AEPF_v0.1_WORKING_DRAFT.md` (lock commit `65c8035`).

---

*End of result document. Status: RESULT_ERSAF_v1, locked at the commit recording this document.*