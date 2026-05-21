# Pre-registration — Expansion Residual Structure Assessment Framework (ERSAF) v1.0

**Status:** Draft pending lock commit. Transition from Protocol Draft v0.1 to Pre-Registration v1.0 completed after closure of all nine methodological locks.
**Identifier:** `ersaf-cosmology-residual-structure-v1`
**Date:** 2026-05-19.
**Author:** Earl Dixon.

---

## 1. Primary research question

After fitting pre-registered ΛCDM cosmology to pre-registered observational expansion-history datasets using pre-registered covariance handling, do pre-registered residual-organization diagnostics identify statistically significant localized or non-smooth residual organization exceeding covariance-aware ΛCDM mock expectations and standard cosmological extensions?

This is an observational and statistical assessment problem. No mechanism is assumed. No interpretation is assumed. No claim regarding dark energy, oscillatory cosmology, emergent spacetime, or alternative physics is made by this pre-registration. The audit is silent on theoretical frameworks in both verdict directions.

ΛCDM remains the reference cosmological model for the primary analysis; standard smooth cosmological extensions (wCDM, w₀wₐ CDM) are part of the null comparison framework. Null outcomes are treated as scientifically valid outcomes equal in weight to positive outcomes.

---

## 2. Baseline cosmology and parameter fit

### 2.1 Primary baseline: jointly-fit ΛCDM

ΛCDM parameters are jointly fit to the registered datasets (Section 3) via generalized least squares with the full covariance matrix.

**Parameters fit:** H₀, Ωₘ.

**Fixed parameters:**
- Ωᵦh²: fixed at 0.02237 (Planck 2018 results VI, Table 2 column 4, TT,TE,EE+lowE+lensing combination, 68% CL uncertainty ±0.00015). Stored and consumed as Ωᵦh² directly by the Eisenstein-Hu sound horizon computation; not as Ωᵦ separately multiplied by the analysis's fitted h, since Planck constrains the physical density Ωᵦh² rather than Ωᵦ and reconstructing Ωᵦh² via the analysis's own H₀ posterior would introduce a spurious dependence on the fit when Ωᵦh² is supposed to be a fixed external prior.
- Curvature: flat (Ωₖ = 0).

**Residual construction:** observation minus best-fit ΛCDM prediction at each observation point.

**Joint-fit tension handling.** The Hubble tension between Planck-anchored and Pantheon+-anchored H₀ estimates does not disappear under a joint fit — it relocates into a compromise value that neither dataset alone prefers, producing systematic patterns in residuals that are real signal artifacts of the joint-fit procedure rather than noise. The covariance-aware null mock procedure (Section 5) refits ΛCDM jointly on every mock realization using the same generalized least squares procedure, so that the null distribution captures any structure produced by the joint-fit's compromise on inter-dataset tension. The observed structure is compared against this procedure-aware null, not against a naive Gaussian null.

**Solver specifics.**
- Implementation: `scipy.optimize.least_squares` with trust-region reflective method (`method='trf'`). Levenberg-Marquardt (`method='lm'`) is incompatible with the parameter bounds specified below and in §7.3 (LM does not support bounded fits); `trf` is the bound-supporting method and is the locked choice. Alternative `iminuit` with Migrad is acceptable and recorded at lock-commit time.
- Initial values: H₀ = 70, Ωₘ = 0.3.
- Bounds: H₀ ∈ [1, 200], Ωₘ ∈ [0.01, 0.99].
- Convergence tolerance: `xtol = 1e-6` (relative parameter change).
- Function-evaluation limit: `max_nfev = 100`. `scipy.optimize.least_squares` does not expose a direct iteration cap; the function-evaluation cap is the closest deterministic limit and is set at the literal value 100 (not scaled by the number of parameters).

### 2.2 Secondary sensitivity analysis: Planck-fixed parameters

In addition to the primary jointly-fit analysis, a secondary sensitivity analysis with ΛCDM parameters fixed to the Planck 2018 best-fit values (TT,TE,EE+lowE+lensing combination) is pre-registered. The secondary analysis is performed regardless of the primary outcome, with its result reported alongside the primary verdict. The secondary's purpose is to disclose, before any result is observed, how the analysis would have behaved had a Planck-fixed baseline been chosen.

### 2.3 Acknowledged structural blind spot

The flat-curvature assumption (Ωₖ = 0) means the test is structurally insensitive to nonzero curvature signatures. If real curvature exists, it could appear in residuals as a slow drift that the diagnostics may or may not flag depending on how localized they are. This is an acknowledged blind spot, not a closed-off rescue path. The question being answered is "is there non-smooth organization beyond flat ΛCDM" rather than "beyond ΛCDM in general."

---

## 3. Datasets and covariance

### 3.1 Observational datasets

**(a) Pantheon+ Type Ia supernova compilation** (Brout et al. 2022).
- Configuration: unanchored. The SH0ES Cepheid anchor is not used.
- Absolute magnitude: M_B is analytically marginalized from the SN χ² using the closed-form Gaussian marginalization formula

      χ²_SN_marg = Δμᵀ C_SN⁻¹ Δμ − (1ᵀ C_SN⁻¹ Δμ)² / (1ᵀ C_SN⁻¹ 1)

  where Δμ = μ_obs − μ_pred(θ_cosmo, M_B = 0). This is mathematically equivalent under Gaussian likelihood to fitting M_B as a free parameter and reporting the marginal posterior on the remaining cosmological parameters; it is the standard treatment used in the Pantheon+, JLA, and Union analyses (Brout et al. 2022; Conley et al. 2011; Betoule et al. 2014). The joint χ² minimized by the fit is χ²_SN_marg + χ²_BAO; both are functions of the cosmological parameters only. The marginalization is exact for ERSAF because the §3.2 block-diagonal joint covariance makes the SN and BAO contributions independent. M_B is treated as a single global scalar across all surveys (no survey-specific M_B offsets beyond those already absorbed into the published Pantheon+ corrections). The marginalized best-fit value M̂_B = (1ᵀ C_SN⁻¹ Δμ) / (1ᵀ C_SN⁻¹ 1), computed post-fit at the converged cosmological best-fit, is stored in the lock-commit manifest (§11) for diagnostic purposes; it does not enter any significance test or the residual signal consumed by §4.
- Redshift floor: z > 0.01. Supernovae at or below z = 0.01 are excluded to mitigate the very-low-redshift regime where peculiar velocity corrections dominate.
- Covariance: full systematic-included covariance matrix (`Pantheon+SH0ES_STAT+SYS.cov` or equivalent published systematic covariance). Statistical-only covariance is not used.
- Acknowledged systematic: peculiar-velocity-correction model dependence in the z > 0.01 retained sample is partially but not fully captured in the published covariance.

**(b) DESI BAO measurements from DR1.** The data vector spans two papers in the DESI 2024 publication series:
  - **Galaxy and quasar BAO** (Adame et al. 2024, DESI 2024 III, arXiv:2404.03000): six redshift bins covering BGS (z ≈ 0.295), LRG (z ≈ 0.51 and 0.706), LRG+ELG (z ≈ 0.93), ELG (z ≈ 1.32), and QSO (z ≈ 1.49), contributing ten of the twelve observables.
  - **Lyman-α forest BAO** (Adame et al. 2024, DESI 2024 IV, arXiv:2404.03001): one redshift bin at z ≈ 2.33, contributing the remaining two observables.

  Together, the data vector is all twelve published BAO observables corresponding to the seven DR1 redshift bins. Five bins (LRG×2, LRG+ELG, ELG, Lyα) publish both D_M/r_d and D_H/r_d separately; the remaining two bins (BGS, QSO) publish a single observable (D_V/r_d or equivalent). The exact split per bin is recorded in the lock manifest at setup time per §11; the pre-registration commits to "the twelve observables published in DR1" without committing in advance to a specific per-bin structure that would need to be re-verified against the actual release.

- Each observable is treated with its published covariance; the joint 12×12 BAO covariance is assembled block-diagonal across the seven bins with each bin's internal 1×1 or 2×2 covariance block preserving the published within-bin correlations (the LRG+ELG joint bin at z ≈ 0.93 has a non-diagonal 2×2 D_M-D_H sub-block that is loaded verbatim from the source rather than reconstructed).
- Materialization source: the DESI DR1 BAO measurements are loaded from the community-maintained `CobayaSampler/bao_data` repository, pinned by commit SHA at lock time (recorded in §11). The materialization converter additionally encodes the published Table 1 values from DESI 2024 III and DESI 2024 IV as a verification anchor — each loaded value is asserted to match the published value within its published precision before the materialized CSV is written. This places three audit surfaces on the data acquisition step (converter logic, the published-value verification dict, and the assertion tolerance choice).
- Secondary analysis: excluding the Lyα observables (DESI 2024 IV contribution) is pre-registered and reported alongside the primary verdict regardless of outcome.

### 3.2 Joint covariance

Joint covariance is block-diagonal:
- Pantheon+ block of size N_post-cut × N_post-cut, where N_post-cut is the count of supernovae retained after the z > 0.01 cut.
- DESI BAO block of size 12 × 12 (twelve observables across seven redshift bins per §3.1).
- Zero cross-survey correlation between the two blocks.

The block-diagonal structure is explicitly disclosed as a standard-practice assumption rather than a derived property. Cross-survey correlation between Pantheon+ and DESI BAO is treated as negligible per current cosmological analysis convention.

### 3.3 Dataset version pinning

Final dataset versions are verified against current public documentation at lock-commit time. The exact release identifier, data URL, and SHA-256 hash of the materialized observational data are recorded in the lock-commit manifest.

---

## 4. Diagnostic battery

The audit applies four diagnostic families to the residuals defined in Section 2. The diagnostics are computed on different aspects of the residual structure and combined via the multiple-testing correction in Section 6.

### 4.1 Binning (shared input for Sections 4.2 – 4.4)

After the z > 0.01 cut from Section 3, the surviving Pantheon+ supernovae are sorted by redshift and grouped into 20 bins of equal supernova count. Each bin's mean residual and standard error are computed; the standard error is derived from the GLS-fit propagation of Section 3's full covariance, not from the empirical scatter of the binned means. The result document MUST report each bin's z-range so a reader can map diagnostic outputs back to redshift.

### 4.2 Localized decomposition: wavelet CWT (Lock 3)

**Method.** Continuous wavelet transform (CWT) with the Mexican hat (DOG-2, second derivative of a Gaussian) mother wavelet, applied to the 20-bin Pantheon+ residual signal.

**Parameters.**
- Scale range: 1 bin (smallest detectable feature) to 7 bins (Torrence & Compo 1998 recommended upper bound of approximately one-third the signal length).
- 32 logarithmically-spaced scales within that range.
- Boundary condition: symmetric extension.
- Cone of influence (COI): coefficients within the COI at each scale are masked from significance assessment per the Torrence & Compo (1998) e-folding criterion for the DOG(m=2) Mexican hat wavelet, with COI half-width at each scale computed as `coi_width = ceil(scale × sqrt(m + 0.5)) = ceil(scale × sqrt(2.5)) ≈ 1.58 × scale` bins from each edge. On a 20-bin signal with the locked scale range 1–7, this means scales above approximately 5 bins have zero coefficients outside the COI and are not testable. The diagnostic is therefore insensitive by construction to residual structure whose characteristic length exceeds ~5 bins (~one-quarter of the signal length). This is an acknowledged structural blind spot of the wavelet diagnostic on the locked signal length (see §9.6); broader structures could be tested only by extending the signal length, which would require a different supernova compilation than Pantheon+ or a different binning resolution than 20 equal-population bins, neither of which is in scope for ERSAF v1.

**Significance test.** All wavelet coefficients outside the COI are tested individually against their respective null distributions from Section 5. No aggregate statistic (maximum, summed magnitude, or otherwise) is substituted for the per-coefficient tests. Per-coefficient significance is computed as a two-sided p-value:

p = 2 × min(P(c_mock ≥ c_obs), P(c_mock ≤ c_obs))

clipped at 1.0. The set of per-coefficient p-values is passed to the Section 6 multiple-testing correction procedure.

**Implementation consistency.** The same CWT implementation, library version, boundary-condition handling, and scale grid are used for the binned data signal and every null mock realization. Implementation specifics are recorded in the lock-commit's environment manifest.

**Acknowledged conventional choices.** The 20-bin grouping, the 32-scale resolution, and the 1-to-7-bin scale range are conventional values; 15 bins or 25 bins, 24 scales or 40 scales, and slightly different scale ranges would all be defensible. The methodology pattern is sound; these specific parameter values are conventional defaults, not first-principles-derived values.

### 4.3 Change-point detection: PELT (Lock 4)

**Method.** PELT (Pruned Exact Linear Time) algorithm applied to the 20-bin Pantheon+ residual signal.

**Cost function.** Gaussian mean-shift likelihood. The cost function uses per-bin standard errors derived from the GLS-fit propagation of Section 3's full covariance, not the empirical scatter of the binned means.

**Penalty.** BIC penalty. The exact numerical penalty value from the `ruptures` library's BIC implementation is verified against the library's documentation at lock-commit time and recorded in the manifest (not as "BIC" abstractly, but as the literal numerical constant used).

**Minimum segment length.** 2 bins. Segments of length 1 are not permitted.

**Test statistic.** The number of change-points detected in the binned signal. The detected change-point *locations* are recorded in the analysis output for descriptive purposes but are not used as test statistics; only the count enters the significance test.

**Significance.** Two-sided empirical p-value comparing the observed count to the null mock distribution: p = 2 × min(P(count_mock ≥ count_obs), P(count_mock ≤ count_obs)), clipped at 1.0.

**Implementation consistency.** The same `ruptures` library version, same cost-function implementation, same penalty, and same minimum-segment-length parameter are used for the binned observed signal and every null mock realization. Library version recorded in the manifest.

**Acknowledged power limitation.** The count statistic on a 20-point signal under BIC penalty has limited discriminating power. The null distribution is expected to be heavily concentrated at low integer values (typically 0 to 2 with rare excursions higher), and the test is therefore informative primarily when the observed structure produces substantially more change-points than chance. A null outcome from this diagnostic is informative but does not strongly constrain the existence of regime transitions that produce only one or two change-points.

### 4.4 Autocorrelation: Pearson ACF (Lock 5)

**Method.** Pearson autocorrelation coefficient (unweighted, standard formulation, biased estimator), applied to the 20-bin Pantheon+ residual signal.

**Estimator.** Pearson, with `adjusted=False` (biased estimator) in the `statsmodels.tsa.stattools.acf` implementation. The biased estimator is conventionally preferred for small samples because it has lower variance and is more conservative for significance testing. Spearman or weighted variants are not used.

**Lag set.** Lags 1, 2, 3, 4, 5. Lag k uses 20 − k pairs. Lags above 5 are not tested.

**Preprocessing prohibition.** ACF is computed on the raw 20-bin residual series directly. No detrending, differencing, or other preprocessing is applied prior to ACF computation. The binned residuals are already a kind of detrended signal (observation minus best-fit cosmology); additional preprocessing would absorb structure the diagnostic is looking for.

**Test statistic.** Autocorrelation coefficient at each individual lag. Each lag's observed coefficient is compared to the empirical null distribution at that lag from the covariance-aware mock realizations (Section 5). The Ljung-Box joint statistic is not used in place of per-lag testing.

**Significance.** Two-sided p-value at each lag: p = 2 × min(P(r_mock ≥ r_obs), P(r_mock ≤ r_obs)), clipped at 1.0.

**Implementation consistency.** The same ACF implementation, library version, and parameters are used for the binned observed signal and every null mock realization. At lock-commit time, the `statsmodels` API conventions are verified against the pinned library version (the `adjusted` parameter name and default value have changed across versions; the exact pinned version is recorded).

**Acknowledged sensitivity limitation.** The autocorrelation diagnostic is sensitive to dependence at the locked lags and may miss dependence at longer lags or non-linear forms of dependence (e.g., higher-order moments). The choice of Pearson over Spearman implicitly tests linear magnitude-dependence rather than monotone rank-dependence. A null outcome from this diagnostic is informative for linear lag-1-through-5 dependence under Gaussian-like residual assumptions but does not constrain non-linear or higher-lag structure.

### 4.5 BAO per-point assessment (Lock 3)

The twelve DESI BAO observables are assessed individually. Each BAO residual is compared to the null-mock distribution at the same observable, with two-sided p-value computed as above. No wavelet, change-point, or autocorrelation analysis is applied to the BAO data given the small number of observables and irregular redshift spacing. The twelve per-observable p-values join the Section 4.2–4.4 results in the Section 6 multiple-testing correction procedure. The result document MUST report each observable's redshift, observable type (D_M/r_d, D_H/r_d, or D_V/r_d), and bin association so a reader can map BAO firing back to the published DR1 measurements.

---

## 5. Covariance-aware null framework

### 5.1 Mock count and master seed

**Mock count:** 10,000 realizations.

**Master seed:** 150914 (continues the convention used in prior pre-registrations in this repository).

**Sub-seed generation:** `numpy.random.SeedSequence(150914).spawn(10000)`. Mock i uses sub-seed i, regardless of parallelization. Re-running the analysis with the same locked code, same data hashes, and same library versions produces bitwise-identical mock realizations.

### 5.2 Mock generation procedure per realization i

1. Use sub-seed i to seed a numpy `Generator`.
2. Draw z_i ~ N(0, I) of length N_post-cut + 7, where N_post-cut is the Pantheon+ supernova count after the Section 3 z > 0.01 cut, determined at setup time and recorded in the lock manifest.
3. Compute mock residuals: r_mock,i = L @ z_i, where L is the cached Cholesky factor of the block-diagonal Section 3 covariance.
4. Construct mock observations: obs_mock,i = best-fit-ΛCDM-prediction-to-observed-data + r_mock,i.
5. Refit ΛCDM jointly to obs_mock,i using the same GLS procedure as Section 2, same solver (`scipy.optimize.least_squares` with `method='trf'`), same `xtol = 1e-6`, same `max_nfev = 100`, same initial values (H₀ = 70, Ωₘ = 0.3), same parameter bounds.
6. Compute final mock residuals: r_final_mock,i = obs_mock,i − ΛCDM_mock_fit_prediction.
7. Apply Section 4.1 binning (20 equal-population bins on SN side), then compute all diagnostic statistics from Sections 4.2 – 4.5: wavelet CWT coefficients outside COI, PELT change-point count, ACF values at lags 1-5, BAO per-point residuals.
8. Store the per-mock statistics in a single HDF5 or Parquet file: wavelet coefficient values outside the COI, PELT change-point count, ACF values at lags 1-5, BAO per-point residuals. Mock-fit parameter values (H₀_mock,i, Ωₘ_mock,i) are also stored for diagnostic purposes but do not enter any significance test.

The cached Cholesky factor L is computed once at setup from the block-diagonal Section 3 covariance; it is not recomputed per mock.

### 5.3 Setup-time verification

Before any mock is generated, the setup procedure verifies that the block-diagonal joint covariance is numerically positive-definite. The smallest eigenvalue is checked; if the matrix is borderline (smallest eigenvalue below a small positive threshold), the setup aborts with a clear error message rather than proceeding to a Cholesky decomposition that would fail or produce unstable mocks.

### 5.4 Convergence failure handling

At 10,000 mocks with a 100-iteration limit and 1e-6 tolerance, some small fraction of mock fits may fail to converge. Failed-convergence mocks are recorded as failures, excluded from the null distribution, and the total failure rate is reported in the result document. If the failure rate exceeds 1% of mocks, the analysis is paused and reconsidered before proceeding. This policy prevents silent bias in the null distribution from convergence failures correlated with realization properties.

### 5.5 Monte Carlo precision floor

At 10,000 mocks, p-values below approximately 10⁻⁴ are dominated by Monte Carlo noise. Such values are reported as "p < 10⁻⁴" rather than as specific numerical values. The multiple-testing correction thresholds (Section 6) typically fall at significantly higher p-values where Monte Carlo precision is adequate.

### 5.6 Computational budget

Estimated single-thread runtime: ~2 seconds per mock, ~5.5 hours for 10,000 mocks. With 8-core parallelization: ~40 minutes. The full analysis (three baseline cosmologies × 10,000 mocks each per Section 7) is estimated at ~2 hours on 8-core hardware. The analysis is expected to be run in a single batch after the lock commit.

---

## 6. Multiple-testing correction and cross-diagnostic combination

### 6.1 Within-diagnostic correction (primary FWER)

Each diagnostic family applies Bonferroni correction at α = 0.05 to its own set of tests:

- **Wavelet (Section 4.2):** per-coefficient threshold p_corrected ≤ 0.05 / N_coef, where N_coef is the number of coefficients outside the cone of influence. N_coef is determined at run time and recorded in the analysis manifest.
- **PELT (Section 4.3):** single test; no within-diagnostic correction. Threshold p ≤ 0.05.
- **ACF (Section 4.4):** per-lag threshold p_corrected ≤ 0.05 / 5 = 0.01.
- **BAO per-point (Section 4.5):** per-observable threshold p_corrected ≤ 0.05 / 12 ≈ 0.00417. (More stringent than the prior 0.05/7 reflecting the actual 12-observable structure of the DR1 data vector per §3.1 amendment; this is correct conservative behavior — more individual tests bear a smaller per-test share of the family-wise error budget.)

A diagnostic family "fires" if at least one of its tests achieves p_corrected at or below its within-diagnostic Bonferroni threshold (inclusive of equality).

### 6.2 Cross-diagnostic combination

ERSAF reports a positive verdict at the analytical level if at least 2 of the 4 diagnostic families fire under the primary FWER procedure. Fewer than 2 firing constitutes a null verdict. Which specific diagnostics fired is reported regardless of the combined verdict.

### 6.3 Secondary FDR disclosure

Independently and in parallel to the FWER-based primary verdict, Benjamini-Hochberg (BH) FDR correction at q = 0.05 is applied within each diagnostic family. The BH-corrected result per diagnostic and the cross-diagnostic BH verdict are reported in the result document as a secondary disclosure. The BH disclosure does not override the primary FWER verdict; it provides a sensitivity reference. The BH procedure assumes positive regression dependence (PRDS) between tests within a diagnostic; the wavelet's correlated coefficients are believed to satisfy PRDS approximately but this is an assumption rather than a derived property.

### 6.4 Implementation

Multiple-testing correction implemented via either `scipy.stats.false_discovery_control(method='bh')` or `statsmodels.stats.multitest.multipletests`. The exact choice is pinned at lock-commit time and the library version recorded.

### 6.5 Acknowledged combination-rule limitation

The 2-of-4 combination rule does not strictly control any standard error-rate quantity. It is a pre-registered heuristic chosen to be substantially more conservative than 1-of-4 single-diagnostic firing while not requiring full unanimity across diagnostic families. The four diagnostics are not strictly independent — they probe overlapping aspects of the same residual series, and the wavelet and ACF are mathematically related (ACF coefficients are linear combinations of certain wavelet integrals). The actual joint false-positive rate of the combination rule under the null is not analytically derivable. The rule's role is to guard against single-diagnostic artifacts, not to deliver a calibrated overall α value.

---

## 7. Standard extension comparison and combined positive-verdict criteria

### 7.1 Extensions compared

**wCDM:** constant equation of state w ≠ −1, additional parameter w fit jointly.

**w₀wₐ CDM:** CPL parameterization w(z) = w₀ + wₐ × z/(1+z), additional parameters w₀ and wₐ fit jointly.

These are the most widely-used phenomenological extensions to ΛCDM in current cosmological analysis. They are not exhaustive of possible dark-energy or alternative-physics extensions; the comparison is bounded to these two specific models.

### 7.2 Procedural design

For each extension, the complete analysis pipeline (Sections 2 – 6) is re-run with the alternative cosmology in place of ΛCDM:

(a) Joint GLS fit of the alternative-cosmology parameters to the same Pantheon+ + DESI BAO data with the same Section 3 covariance treatment.

(b) Computation of residuals against the alternative-cosmology best-fit prediction.

(c) Generation of 10,000 mock realizations using the alternative cosmology, with the same master seed `SeedSequence(150914).spawn(10000)`. The same per-mock refit procedure is applied; the residuals differ across cosmologies because the baseline prediction differs.

(d) Application of the Section 4 diagnostic battery.

(e) Application of Section 6 within-diagnostic Bonferroni correction.

This is a parallel analysis with the alternative cosmology as the new baseline. The methodology pattern is identical to the ΛCDM analysis; only the baseline model changes.

### 7.3 Parameter sets and bounds

- **wCDM:** fit (H₀, Ωₘ, w). Ωᵦ Planck-fixed. Flat curvature. Bounds: H₀ ∈ [1, 200], Ωₘ ∈ [0.01, 0.99], w ∈ [-3, 0]. Initial values: H₀ = 70, Ωₘ = 0.3, w = −1.
- **w₀wₐ CDM:** fit (H₀, Ωₘ, w₀, wₐ). Ωᵦ Planck-fixed. Flat curvature. Bounds: H₀ ∈ [1, 200], Ωₘ ∈ [0.01, 0.99], w₀ ∈ [-3, 0], wₐ ∈ [-3, 3]. Initial values: H₀ = 70, Ωₘ = 0.3, w₀ = −1, wₐ = 0.

The initial values place the optimizer at the ΛCDM-equivalent point of each extension, ensuring consistent solver behavior across baselines.

### 7.4 Sound horizon r_d computation

Sound horizon r_d is computed via the Eisenstein & Hu 1998 fitting formula at every fit iteration. The fitting formula assumes the standard radiation-matter transition history and is applied identically under ΛCDM, wCDM, and w₀wₐ CDM. This is acknowledged as an approximation under w₀wₐ where dark-energy evolution could in principle perturb pre-recombination dynamics, though the effect at the drag epoch is small for the parameter ranges of interest. Verification against a CAMB/CLASS-based numerical computation is not part of ERSAF.

### 7.5 Paired-mock structure across baselines

Mock realizations are paired across the three baseline cosmologies: mock i under ΛCDM, wCDM, and w₀wₐ CDM shares the same Gaussian noise vector z_i. The three sets of mock observations differ only in their baseline-cosmology prediction. This paired structure is intentional and provides cleaner comparison across baselines than independent mock generation would. It does mean the three null distributions are not statistically independent of each other.

### 7.6 Family-level survival criterion

A diagnostic family "survives" an extension if at least one of its tests achieves Bonferroni-corrected significance under that extension's analysis. The specific tests need not match the tests that were significant under ΛCDM; the family-level firing must persist. This criterion implements the original protocol's intent: filter smooth trends absorbed by extensions while not requiring exact pattern reproduction across baselines (which would be overly strict given that residuals are different by construction under different cosmologies).

### 7.7 Combined positive-verdict criteria

ERSAF reports a positive analytical verdict if and only if all three conditions hold:

1. **The Section 6 ΛCDM verdict is positive.** At least 2 of the 4 diagnostic families fire under ΛCDM via Bonferroni-corrected FWER at α = 0.05.

2. **Under wCDM, the same diagnostic families fire.** Each family that fired under ΛCDM has at least one corrected-significant test under wCDM.

3. **Under w₀wₐ CDM, the same diagnostic families fire.** Same family-level criterion as wCDM.

Partial-survival outcomes (some firing families absorbed by extensions, others surviving) are reported descriptively in the result document but do not constitute a positive ERSAF verdict. A null verdict is the appropriate classification for any outcome that fails to meet all three conditions.

### 7.8 Reporting requirements for the extension comparison

The result document MUST report, for each baseline cosmology (ΛCDM, wCDM, w₀wₐ CDM):
(a) The fitted parameter values.
(b) For each diagnostic family, whether it fires under the within-diagnostic Bonferroni correction.
(c) The secondary BH FDR result.

The combined positive-verdict criteria above produce the headline ERSAF verdict.

---

## 8. Audit boundary

This audit tests, and only tests, whether residual organization survives the methodology specified in Sections 2 – 7 on the datasets specified in Section 3.

The audit does NOT test:

- Whether residual organization, if detected, reflects new physics. ERSAF measures statistical significance against specified nulls; it does not measure whether the signal has a physical cause beyond known systematics.
- Whether dark energy has non-smooth evolution. The two extensions tested are widely-used phenomenological forms; many other extensions exist.
- Whether ΛCDM is correct as a complete cosmological framework. ERSAF tests only the expansion-history residuals from Type Ia supernovae and BAO; other ΛCDM predictions (CMB, structure growth, lensing, cluster counts) are not evaluated.
- Whether observational systematics absent from the published Pantheon+ and DESI covariance matrices have been accounted for. The covariance encodes the published systematic-uncertainty estimates; effects not captured there are not addressed by this audit.
- Whether anisotropies or sky-position dependence exist in the residuals. ERSAF treats residuals as a one-dimensional function of redshift only.

---

## 9. Interpretive constraints

Regardless of which verdict ERSAF produces, the result document MUST observe the following interpretive constraints. These constraints are binding components of the pre-registration: the result document cannot validly claim more than they permit, regardless of how striking or unfavorable the analytical verdict is.

### 9.1 What a POSITIVE ERSAF verdict establishes

- That on Pantheon+ (Brout et al. 2022, unanchored configuration, post-z > 0.01 cut) combined with DESI DR1 BAO (Adame et al. 2024, DESI 2024 III + IV, arXiv:2404.03000 and 2404.03001, all twelve observables across seven redshift bins), at the dataset revisions verified at lock-commit, under the joint GLS fit specified in Section 2 with the block-diagonal covariance specified in Section 3, at least 2 of 4 diagnostic families detect residual patterns whose corrected p-values fall at or below the within-diagnostic Bonferroni-FWER thresholds at α = 0.05.
- That those same diagnostic families also fire (at any specific within-family test) when wCDM and w₀wₐ CDM replace ΛCDM as the baseline cosmology under identical methodology.
- That the joint-fit compromise on inter-dataset tension does not, by itself, produce the detected structure: the same-procedure null mocks capture the joint-fit's tension-driven artifact, and the observed structure exceeds that null distribution.

### 9.2 What a POSITIVE ERSAF verdict does NOT establish

- That the detected residual organization reflects new physics. ERSAF measures statistical significance against specified nulls; it does not test physical causation.
- That dark energy has non-smooth evolution. The two extensions tested are widely used but not exhaustive. Other extension forms — quintessence with non-trivial potentials, early dark energy, interacting dark sector models, modified gravity, time-varying fundamental constants — could in principle absorb the detected structure under their own parameter freedoms.
- That ΛCDM is incorrect as a complete cosmological framework. ERSAF tests only expansion-history residuals; other ΛCDM predictions remain unevaluated.
- That the operator's prior conceptual program — including "coherence," "MCC/CI," "structural commitment," cyclic cosmology, or emergent spacetime — is correct. The audit measures residual structure; it does not test any interpretation of what that structure means. Connecting an ERSAF positive verdict to a theoretical framework is post-hoc interpretation, not a result of the audit.
- That the structure exists beyond the locked dataset versions. Subsequent releases of Pantheon+ or DESI may differ in systematic treatments, additional supernovae, or revised covariance structures, and could change the analytical conclusion.
- That the structure exists at all redshifts. ERSAF tests the redshift range covered by the registered datasets only.
- That observational systematics absent from the published covariance matrices have been ruled out as alternative explanations.
- That the Eisenstein-Hu sound horizon approximation is exact under w₀wₐ CDM.

### 9.3 What a NULL ERSAF verdict establishes

- That under the specific methodology of this audit, no statistically significant non-smooth residual organization was detected via the Section 7 combined criteria.
- In the specific case where ΛCDM fires but extensions absorb the structure: that the detected ΛCDM residual organization is consistent with smooth dark-energy evolution under wCDM or w₀wₐ CDM.
- That the cumulative analysis places observational constraints on the existence of detectable non-smooth ΛCDM-deviation at the sensitivity of this specific test on these specific datasets.

### 9.4 What a NULL ERSAF verdict does NOT establish

- That ΛCDM is correct. Absence of detection is consistent with: structure existing at sensitivity below the audit's noise floor; structure existing at scales (redshift ranges, length scales) where the diagnostic battery is insensitive; structure existing in forms (non-linear dependence, higher-order moments, anisotropies) the locked diagnostics do not probe; sample sizes too small for the existing structure to reach corrected significance.
- That alternative cosmological models are ruled out. ERSAF compares ΛCDM against only two specific phenomenological extensions.
- That observational systematics do not drive the residuals.
- That future surveys would replicate the null.
- **That the operator's prior conceptual program — or any specific theoretical framework, including "coherence," "MCC/CI," "structural commitment," cyclic cosmology, or emergent spacetime — is refuted by a null verdict.** The audit measures residual structure in the locked datasets under the locked methodology; it does not test any theoretical framework. A null verdict provides no evidence for or against any framework that proposes mechanisms for the same observable. The framework-silent posture is symmetric across both verdict directions.

### 9.5 Required disclosures in the result document

The result document MUST disclose:

- All locked parameter values and procedural choices from Sections 2 – 7, with explicit version verifications for libraries and dataset releases used at run time.
- The per-diagnostic, per-baseline outcome table: which diagnostics fire under ΛCDM, wCDM, and w₀wₐ CDM, with both Bonferroni-FWER primary and BH-FDR secondary results.
- The Monte Carlo precision floor (~10⁻⁴ from 10,000 mocks).
- All blind spots and known systematics enumerated in Section 9.6.
- The convergence failure rate from mock generation (per Section 5); if > 1%, the analysis pause and reconsideration protocol from Section 5 was triggered.
- The Eisenstein-Hu r_d approximation under w₀wₐ.
- The paired-mock structure across the three baseline cosmologies.
- The 2-of-4 rule's nature as a pre-registered heuristic without analytical false-positive-rate guarantee.
- The PELT count-statistic power limitation on a 20-point signal under BIC penalty.

### 9.6 Known systematics and blind spots

**Partially addressed (encoded in covariance, not exhaustively):**

- Peculiar velocity corrections at low redshift. The z > 0.01 cut excludes the worst-affected supernovae, but residual peculiar-velocity model dependence is not fully captured in the published covariance.
- Photometric calibration cross-survey systematics. Partially encoded in Pantheon+'s published systematic covariance.
- Host-galaxy mass step. Pantheon+'s published corrections account for the mass-step systematic to first order; debates persist over higher-order treatments.
- BAO reconstruction algorithm choices. DESI's published BAO measurements include systematic uncertainty estimates from the reconstruction algorithm.

**Not addressed (acknowledged blind spots):**

- Flat curvature assumption (Section 2.3). The test is structurally insensitive to nonzero curvature signatures.
- Eisenstein-Hu r_d approximation under evolving dark energy (Section 7.4).
- Non-linear dependence structures in residuals (Section 4.4 tests linear ACF only).
- Higher-lag dependence beyond lag 5 (Section 4.4).
- Cosmological parameter degeneracies that the (H₀, Ωₘ) fit does not isolate but that influence residual structure.
- Survey selection effects beyond those captured in the published covariance matrices.
- Anisotropies and directional dependence: ERSAF treats residuals as a one-dimensional function of redshift only. Sky-position dependence is not analyzed.
- Diagnostic battery limitations: the audit's four diagnostic families (wavelet CWT, PELT, ACF, BAO per-point) are a small enumerated set chosen for methodological tractability and standardization. Structural organization detectable by methods outside this battery — Bayesian change-point analysis, Gaussian-process residual modeling, spectral coherence methods, irregular-sampling wavelet variants, or other approaches — is not tested.
- Broad-feature insensitivity of the wavelet diagnostic on the locked signal length. Under the T&C 1998 e-folding COI criterion locked in §4.2, wavelet scales above approximately 5 bins on a 20-bin signal have zero testable coefficients. ERSAF's wavelet diagnostic is therefore structurally insensitive to residual organization whose characteristic redshift extent exceeds approximately one-quarter of the locked signal length. The other three diagnostic families (PELT, ACF, BAO per-point) provide partial coverage of broader-scale structure (PELT detects regime transitions of any width, ACF detects long-range correlation up to lag 5, BAO per-point detects discrete-redshift deviations) but no single locked diagnostic isolates broad smooth bumps. This is an acknowledged scope limit of ERSAF v1; future work with longer signals (larger supernova compilations, finer binning) or different localized-decomposition methods could probe the missing scale range.
- Other cosmological observables: ERSAF is one specific test on one specific data combination. CMB direct constraints, structure-growth measurements, weak lensing surveys, cluster counts, and other cosmological probes are not part of this audit.

The audit's verdict is bounded by these limits. Conclusions drawn beyond these limits are not supported by the test, regardless of which verdict the test produces.

---

## 10. Operational notes

**Pre-lock integrity.** No diagnostic statistics have been computed on the observed Pantheon+ + DESI BAO data prior to the lock commit. The setup phase (Section 11) materializes the data, computes its SHA-256, verifies positive-definiteness of the joint covariance, computes the Cholesky factor, and pins library versions, but does not run the diagnostic battery on observed or mock data.

**Post-lock modifications.** The cosmological parameter choices, dataset choices, covariance treatment, diagnostic specifications, multiple-testing correction procedure, extension comparison procedure, and interpretive constraints MUST NOT be modified between the lock commit and the result document commit. Operational fixes (dependency updates, runtime environment configuration, OpenMP-conflict workarounds analogous to prior audits) that do not alter methodology are permitted but MUST be disclosed in the result document.

**Re-running for reproducibility.** The analysis is fully deterministic given the pinned dataset versions and library versions and the locked seed. Re-running the analysis should produce numerically equivalent outputs within float-precision tolerance.

**Single execution.** The audit is run once after the lock commit. The result document records that single execution. Re-runs for reproducibility verification do not produce new outcome documents.

---

## 11. Provenance

**Author:** Earl Dixon.

**Lock commit:** SHA: 33d18a555b35df93ca86020e2b68f3e334f6b90a.

**Pinned Pantheon+ release:**
- Citation: Brout et al. 2022 (Pantheon+ cosmological-constraints release).
- Source: https://github.com/PantheonPlusSH0ES/DataRelease (`Pantheon+_Data/4_DISTANCES_AND_COVAR/`).
- Configuration: unanchored.
- `Pantheon+SH0ES.dat` SHA-256: `1cb0fc379ef066afdc2ffd1857681cc478024570d8a3eba284fb645775198cf8`.
- `Pantheon+SH0ES_STAT+SYS.cov` SHA-256: `abf806d966485e64afdb359c87bffc0ecc00d05eff0a31ced66f247385df0fdc`.

**Pinned DESI DR1 BAO release:**
- Citations: Adame et al. 2024, DESI 2024 III (arXiv:2404.03000, galaxy/quasar BAO, ten observables) and DESI 2024 IV (arXiv:2404.03001, Lyα forest BAO, two observables).
- Materialization source: `CobayaSampler/bao_data` GitHub repository at commit `bb0c1c9009dc76d1391300e169e8df38fd1096db`. Per-source-file SHA-256s recorded in `analysis/ersaf/data/desi_dr1/materialization_manifest.json`.
- Materialized `desi_dr1_bao.csv` SHA-256: `3c59883352f4cc2ee960b20298c46b8dc8161b97ca8232f7e0449fbeb2e7ddc6`.
- Materialized `desi_dr1_bao_cov.npy` SHA-256: `6a8f9691cf2af65e13d7bf5bd9bc09b4bf06af89e0ae7efdedb66d60fd05470e`.
- Per-bin observable split (the locked structure verified at setup):
  - Bin 1 — BGS, z_eff = 0.295: D_V/r_d.
  - Bin 2 — LRG1, z_eff = 0.510: D_M/r_d, D_H/r_d.
  - Bin 3 — LRG2, z_eff = 0.706: D_M/r_d, D_H/r_d.
  - Bin 4 — LRG3+ELG1, z_eff = 0.930: D_M/r_d, D_H/r_d.
  - Bin 5 — ELG2, z_eff = 1.317: D_M/r_d, D_H/r_d.
  - Bin 6 — QSO, z_eff = 1.491: D_V/r_d.
  - Bin 7 — Lyα, z_eff = 2.330: D_M/r_d, D_H/r_d.

**N_post-cut (Pantheon+ count after z > 0.01 cut):** 1588 (of 1701 in the full release).

**Marginalized best-fit M̂_B per baseline** (closed-form §3.1 formula at converged cosmological best-fit; diagnostic-only, does not enter any significance test):
- ΛCDM:    M̂_B = −19.507083
- wCDM:    M̂_B = −19.605815
- w₀wₐ CDM: M̂_B = −19.504306

**Joint covariance matrix dimensions:** 1600 × 1600 (= 1588 Pantheon+ post-cut block + 12 DESI BAO observables across seven redshift bins per §3.1 amendment).

**Joint covariance SHA-256:** `ac4e18e35e72eefefdf3269f85a3449c05d1e79c720bfb1f518510a5dec7db81`.

**Cholesky factor verification:** smallest eigenvalue of joint covariance = 5.193550 × 10⁻³ (positive-definite check PASS; well above the 10⁻¹² §5.3 threshold).

**Reproducibility manifest:**
- Python: 3.12.10
- numpy: 2.4.6
- scipy: 1.17.1
- pandas: 3.0.3
- statsmodels: 0.14.6
- ruptures: v1.1.10
- PyWavelets (`pywt`): 1.8.0
- GLS solver: `scipy.optimize.least_squares` with `method='trf'`.
- Multi-testing correction implementation: `scipy.stats.false_discovery_control` with `method='bh'`.

**Methodology pattern:** This audit followed the pre-registered methodology pattern documented in `docs/standards/AEPF_v0.1_WORKING_DRAFT.md` (lock commit `65c8035`).

**Companion artifacts (locked together at the lock commit):**

- This pre-registration document.
- `ersaf_analysis.py` (the analysis script).
- `materialize_desi_dr1_bao.py` (the DESI DR1 BAO materialization converter; reads CobayaSampler/bao_data per-tracer files and produces the canonical CSV + covariance .npy, with cross-verification against the Adame+24 III and IV published Table 1 values via an embedded TABLE_1_REFERENCE dict).
- `analysis/ersaf/data/pantheon_plus/Pantheon+SH0ES.dat` (Pantheon+ sample table, unanchored configuration; downloaded directly from PantheonPlusSH0ES/DataRelease).
- `analysis/ersaf/data/pantheon_plus/Pantheon+SH0ES_STAT+SYS.cov` (Pantheon+ STAT+SYS covariance, downloaded directly from PantheonPlusSH0ES/DataRelease).
- `analysis/ersaf/data/desi_dr1/desi_dr1_bao.csv` (the materialized 12-observable DESI DR1 BAO CSV with columns `bin_id, bin_label, z, observable_type, value, error`).
- `analysis/ersaf/data/desi_dr1/desi_dr1_bao_cov.npy` (the materialized 12×12 block-diagonal BAO covariance matrix preserving each bin's internal correlations).
- `analysis/ersaf/data/desi_dr1/materialization_manifest.json` (provenance manifest with the CobayaSampler/bao_data commit SHA, per-source-file SHA-256s, output SHA-256s, and verification-anchor summary).
- `analysis/ersaf/joint_data_sha256.txt` (SHA-256 of all materialized data files plus the constructed joint covariance hash).
- `analysis/ersaf/library_versions.json` (the pinned environment manifest).
- `analysis/ersaf/ersaf_setup_manifest.json` (the full structured §11 setup output including per-bin observable_split, initial fits, and marginalized M̂_B values per baseline).
- `analysis/ersaf/requirements.txt` (Python dependency pinning from `pip freeze`).

---

*End of pre-registration. Status: ERSAF Pre-Registration v1.0, §11 filled from setup-mode output; lock commit pending. All nine methodological locks closed across the cross-model review documented in the session that produced this draft, plus pre-lock amendments to §2.1, §3.1, §3.2, §4.2, §4.5, §5.2, §6.1, §9.1, §9.6, and §11 documented in the conversation history.*