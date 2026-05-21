"""
ersaf_analysis.py — Expansion Residual Structure Assessment Framework

Implements PRE_REGISTRATION_ERSAF_v1.md mechanically. Each non-trivial choice
in this code is traceable to a specific section of the pre-registration.

Modes:
    setup    Materialize Pantheon+ and DESI DR1 BAO data, verify dataset
             versions, compute joint covariance Cholesky factor (with
             positive-definiteness verification), perform initial joint fits
             for ΛCDM/wCDM/w₀wₐ, compute SHA-256 hashes, print TBD values
             for the pre-registration §11.
             No diagnostic statistics are computed on observed data during
             setup, per pre-reg §10 (Pre-lock integrity).

    run      Verify all locked artifacts. Execute the full analysis:
             three baseline cosmologies × 10,000 mocks each, four-diagnostic
             battery per baseline, multiple-testing correction, cross-diagnostic
             combination, extension comparison, verdict computation. Write
             outputs: per-baseline diagnostic summaries, combined verdict,
             provenance manifest.

Pre-registration: PRE_REGISTRATION_ERSAF_v1.md (locked at commit TBD).

NOTE ON DOMAIN-EXPERTISE LIMITS. The cosmological calculations below
(comoving distance integral, sound horizon via Eisenstein-Hu 1998, BAO
distance computations) follow standard textbook formulas with explicit
citations. A working observational cosmologist would verify these
against CAMB/CLASS-based numerical computations for representative
parameter values before relying on the analysis output. This file
implements the methodology pattern; the cosmology-specific numerics
should be cross-checked by domain expertise before the lock commit.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.optimize
import scipy.stats
from scipy.integrate import quad
from scipy.linalg import cholesky, solve_triangular


# ============================================================================
# CONFIGURATION (LOCKED BY PRE-REGISTRATION)
# ============================================================================

# §5.1 — Mock count and master seed
N_MOCKS = 10_000
MASTER_SEED = 150914

# §2 — ΛCDM fit configuration
LAMBDA_CDM_PARAM_NAMES = ["H0", "Om"]
LAMBDA_CDM_INITIAL = {"H0": 70.0, "Om": 0.3}
LAMBDA_CDM_BOUNDS = {"H0": (1.0, 200.0), "Om": (0.01, 0.99)}

# §7.3 — wCDM and w0wa fit configuration
WCDM_PARAM_NAMES = ["H0", "Om", "w"]
WCDM_INITIAL = {"H0": 70.0, "Om": 0.3, "w": -1.0}
WCDM_BOUNDS = {"H0": (1.0, 200.0), "Om": (0.01, 0.99), "w": (-3.0, 0.0)}

W0WA_PARAM_NAMES = ["H0", "Om", "w0", "wa"]
W0WA_INITIAL = {"H0": 70.0, "Om": 0.3, "w0": -1.0, "wa": 0.0}
W0WA_BOUNDS = {
    "H0": (1.0, 200.0),
    "Om": (0.01, 0.99),
    "w0": (-3.0, 0.0),
    "wa": (-3.0, 3.0),
}

# §2.1 — Planck 2018 fixed Ω_b h² value (TT,TE,EE+lowE+lensing, Planck 2018 results VI).
# Reference: Planck 2018 results VI (Aghanim et al. 2020), Table 2 column 4: Ω_b h² = 0.02237 ± 0.00015.
# Stored as Ω_b h² directly per pre-reg §2.1 amendment, because Planck constrains the
# physical density Ω_b h² rather than Ω_b. Reconstructing Ω_b h² via the analysis's own
# fitted h would introduce a spurious dependence on the fit when Ω_b h² is supposed to
# be a fixed external prior. The Eisenstein-Hu 1998 sound horizon formula consumes Ω_b h²
# directly (see sound_horizon_eisenstein_hu_1998).
OMEGA_B_H2_PLANCK_2018 = 0.02237

# §6 — Solver convergence
CONVERGENCE_TOLERANCE = 1e-6
ITERATION_LIMIT = 100

# §3.1 — Redshift cut
Z_FLOOR = 0.01

# §4 — Diagnostic battery parameters
N_BINS = 20            # §4.1 — equal-population bins for SN binning
CWT_WAVELET = "mexh"   # §4.2 — Mexican hat (DOG-2) via PyWavelets
CWT_N_SCALES = 32      # §4.2 — log-spaced scales
CWT_SCALE_MIN = 1.0    # §4.2 — smallest scale in bin units
CWT_SCALE_MAX = 7.0    # §4.2 — largest scale (≈ N_BINS / 3)
PELT_MIN_SEGMENT = 2   # §4.3 — minimum segment length
ACF_LAGS = [1, 2, 3, 4, 5]  # §4.4 — lag set
ACF_ADJUSTED = False   # §4.4 — biased estimator

# §6 — Multiple-testing correction
ALPHA = 0.05
N_DIAGNOSTIC_FAMILIES = 4
COMBINATION_RULE_K = 2  # 2-of-4 combination rule


# ============================================================================
# UTILITIES
# ============================================================================


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def two_sided_empirical_pvalue(observed, mock_distribution):
    """
    Two-sided p-value from empirical null distribution.

    Per §4.2, §4.3, §4.4, §4.5:
        p = 2 × min(P(c_mock ≥ c_obs), P(c_mock ≤ c_obs))
    clipped at the upper bound 1.0 and at the lower Monte Carlo precision
    floor 1 / N_mocks (§5.5). Values at the floor are reported in result
    documents as "p < 1e-4" per §5.5.

    Behavior on discrete-valued statistics (the PELT count). For an
    integer-valued mock distribution, mocks where mock == observed contribute
    to both P(mock ≥ observed) and P(mock ≤ observed), so p_upper + p_lower
    exceeds 1 by twice the tie probability. The two-sided combination
    2 × min(p_upper, p_lower) therefore carries a slight conservative bias
    on discrete statistics. This is acceptable behavior — the bias is in the
    direction of fewer false positives at threshold — but is worth disclosing
    to consumers comparing p-values across continuous and discrete diagnostics.
    """
    mock_dist = np.asarray(mock_distribution)
    n = len(mock_dist)
    p_upper = np.sum(mock_dist >= observed) / n
    p_lower = np.sum(mock_dist <= observed) / n
    p = 2.0 * min(p_upper, p_lower)
    # Upper clip at 1.0; lower clip at the Monte Carlo precision floor 1/N_mocks
    # so "no mock matched" returns the floor rather than zero, and downstream
    # consumers can apply the §5.5 reporting convention uniformly.
    mc_floor = 1.0 / N_MOCKS
    return float(max(min(p, 1.0), mc_floor))


# ============================================================================
# COSMOLOGY (§2, §7)
# ============================================================================
#
# Standard ΛCDM, wCDM, and w0wa cosmological distance calculations. Implementations
# follow textbook formulas; cross-verification against CAMB/CLASS recommended
# before lock commit per the file-level NOTE.

C_LIGHT_KM_S = 299792.458  # km/s


def hubble_function_lambda_cdm(z, params):
    """ΛCDM Hubble function H(z) in units where H_0 = 1.

    H(z) / H_0 = sqrt(Ω_m (1+z)^3 + Ω_Λ)
    with Ω_Λ = 1 - Ω_m under flat curvature (§2.1).
    """
    Om = params["Om"]
    OL = 1.0 - Om
    return np.sqrt(Om * (1.0 + z) ** 3 + OL)


def hubble_function_wcdm(z, params):
    """wCDM Hubble function with constant w (§7.3).

    H(z) / H_0 = sqrt(Ω_m (1+z)^3 + (1 - Ω_m) (1+z)^{3(1+w)})
    """
    Om = params["Om"]
    w = params["w"]
    return np.sqrt(Om * (1.0 + z) ** 3 + (1.0 - Om) * (1.0 + z) ** (3.0 * (1.0 + w)))


def hubble_function_w0wa(z, params):
    """w0wa CDM Hubble function with CPL parameterization (§7.3).

    w(z) = w_0 + w_a × z/(1+z)
    Energy density evolves as:
        ρ_DE(z) / ρ_DE(0) = (1+z)^{3(1+w_0+w_a)} × exp(-3 w_a z/(1+z))
    """
    Om = params["Om"]
    w0 = params["w0"]
    wa = params["wa"]
    de_factor = (1.0 + z) ** (3.0 * (1.0 + w0 + wa)) * np.exp(
        -3.0 * wa * z / (1.0 + z)
    )
    return np.sqrt(Om * (1.0 + z) ** 3 + (1.0 - Om) * de_factor)


def comoving_distance(z, params, hubble_fn):
    """Comoving distance D_C(z) in Mpc.

    D_C(z) = (c / H_0) × ∫_0^z dz' / E(z')
    where E(z) = H(z) / H_0.
    """
    H0 = params["H0"]
    integrand = lambda zp: 1.0 / hubble_fn(zp, params)
    integral, _ = quad(integrand, 0.0, z, epsrel=1e-8)
    return (C_LIGHT_KM_S / H0) * integral


def luminosity_distance(z, params, hubble_fn):
    """Luminosity distance D_L(z) in Mpc.

    D_L(z) = (1 + z) × D_C(z) under flat curvature.
    """
    return (1.0 + z) * comoving_distance(z, params, hubble_fn)


def distance_modulus(z, params, hubble_fn, MB=0.0):
    """Distance modulus μ(z) in magnitudes.

    μ(z) = 5 log10(D_L(z) / 10 pc) = 5 log10(D_L_Mpc × 10^5)
                                   = 5 log10(D_L_Mpc) + 25
    M_B is added as an offset for SN absolute magnitude calibration (§3.1).
    """
    DL = luminosity_distance(z, params, hubble_fn)
    return 5.0 * np.log10(DL) + 25.0 + MB


def sound_horizon_eisenstein_hu_1998(params):
    """Sound horizon at drag epoch via Eisenstein & Hu 1998 fitting formula.

    Per §7.4: applied identically under ΛCDM, wCDM, w0wa CDM.
    Acknowledged as approximation under w0wa.

    EH1998 fitting formula:
        z_eq = 2.5 × 10^4 × Ω_m h^2 (T_CMB/2.7)^{-4}
        k_eq = 7.46 × 10^-2 × Ω_m h^2 (T_CMB/2.7)^{-2}  [Mpc^-1]
        z_d = 1291 × (Ω_m h^2)^{0.251} × [1 + b_1 (Ω_b h^2)^{b_2}]
                / [1 + 0.659 (Ω_m h^2)^{0.828}]
        b_1 = 0.313 (Ω_m h^2)^{-0.419} × [1 + 0.607 (Ω_m h^2)^{0.674}]
        b_2 = 0.238 (Ω_m h^2)^{0.223}
        R(z) = (3 Ω_b h^2) / (4 × 2.469 × 10^-5 × (T_CMB/2.7)^4 × (1+z))
        s = (2 / (3 k_eq)) × sqrt(6 / R_eq)
              × ln[(sqrt(1+R_d) + sqrt(R_d+R_eq)) / (1 + sqrt(R_eq))]
    Returns sound horizon in Mpc.

    Reference: Eisenstein & Hu 1998, ApJ 496, 605, eq. (4)-(7).
    Cross-verify against CAMB/CLASS before relying on the value.
    """
    Om = params["Om"]
    H0 = params["H0"]
    h = H0 / 100.0
    Omh2 = Om * h * h
    # Ω_b h² consumed directly per pre-reg §2.1; do NOT recompute as Ω_b × h² from
    # the fit's h, which would inject a spurious dependence on the analysis's own
    # posterior into what is supposed to be a fixed Planck prior.
    Obh2 = OMEGA_B_H2_PLANCK_2018
    T_CMB = 2.7255  # K, fixed per Planck 2018
    Theta = T_CMB / 2.7

    z_eq = 2.5e4 * Omh2 * Theta ** -4
    k_eq = 7.46e-2 * Omh2 * Theta ** -2  # Mpc^-1

    b1 = 0.313 * Omh2 ** -0.419 * (1.0 + 0.607 * Omh2 ** 0.674)
    b2 = 0.238 * Omh2 ** 0.223
    z_d = 1291.0 * Omh2 ** 0.251 * (1.0 + b1 * Obh2 ** b2) / (
        1.0 + 0.659 * Omh2 ** 0.828
    )

    def R_of_z(z):
        return (3.0 * Obh2) / (4.0 * 2.469e-5 * Theta ** 4 * (1.0 + z))

    R_d = R_of_z(z_d)
    R_eq = R_of_z(z_eq)

    sound_horizon = (2.0 / (3.0 * k_eq)) * np.sqrt(6.0 / R_eq) * np.log(
        (np.sqrt(1.0 + R_d) + np.sqrt(R_d + R_eq)) / (1.0 + np.sqrt(R_eq))
    )
    return sound_horizon  # Mpc


def bao_dm_over_rd(z, params, hubble_fn):
    """Transverse BAO observable D_M(z) / r_d.

    D_M(z) = D_C(z) under flat curvature.
    """
    DC = comoving_distance(z, params, hubble_fn)
    rd = sound_horizon_eisenstein_hu_1998(params)
    return DC / rd


def bao_dh_over_rd(z, params, hubble_fn):
    """Line-of-sight BAO observable D_H(z) / r_d.

    D_H(z) = c / H(z)
    """
    H0 = params["H0"]
    DH = C_LIGHT_KM_S / (H0 * hubble_fn(z, params))
    rd = sound_horizon_eisenstein_hu_1998(params)
    return DH / rd


def bao_dv_over_rd(z, params, hubble_fn):
    """Isotropic BAO observable D_V(z) / r_d.

    D_V(z) = [z × D_M(z)² × D_H(z)]^(1/3)

    Used by DESI DR1 bins that publish a single isotropic D_V/r_d
    measurement rather than separate D_M and D_H (per §3.1 amendment,
    typically the BGS and QSO bins).
    """
    DC = comoving_distance(z, params, hubble_fn)  # D_M = D_C under flat curvature
    DH = C_LIGHT_KM_S / (params["H0"] * hubble_fn(z, params))
    DV = (z * DC * DC * DH) ** (1.0 / 3.0)
    rd = sound_horizon_eisenstein_hu_1998(params)
    return DV / rd


# ============================================================================
# DATA LOADING (§3)
# ============================================================================


def load_pantheon_plus(path_data, path_covariance, unanchored=True):
    """Load Pantheon+ data and covariance matrix (Brout et al. 2022 release).

    Pre-reg §3.1: unanchored configuration. The SH0ES Cepheid anchor is not used;
    M_B is analytically marginalized inside fit_cosmology_joint per the §3.1
    amendment. What the analysis code treats as "mu_obs" is therefore the
    apparent-magnitude column `m_b_corr` from the release; the closed-form
    marginalization absorbs the M_B offset.

    File format expectations (verified against the Brout+2022 GitHub release):

    `path_data` — `Pantheon+SH0ES.dat`: whitespace-separated ASCII with a header
    row. Required columns: `zCMB` (CMB-frame redshift), `m_b_corr` (corrected
    apparent magnitude). Optional column: `IS_CALIBRATOR` (Cepheid-host flag,
    informational only; not filtered out in the unanchored configuration since
    those SNe still contribute valid m_b_corr to the cosmology-only fit).

    `path_covariance` — `Pantheon+SH0ES_STAT+SYS.cov`: text file with the matrix
    dimension N on the first line, followed by N×N floating-point values in
    row-major order (one value per line in the canonical release; this loader
    accepts either one-per-line or whitespace-separated).

    Parameters
    ----------
    path_data : str or Path
        Path to the Pantheon+ sample data file.
    path_covariance : str or Path
        Path to the Pantheon+ STAT+SYS covariance file.
    unanchored : bool, default True
        Whether to use the unanchored configuration per pre-reg §3.1. This is
        the locked ERSAF choice; the parameter exists to make the configuration
        explicit in the call site rather than to support an anchored mode here.

    Returns
    -------
    df : pandas.DataFrame
        Columns: `zCMB` (float), `mu_obs` (float, = `m_b_corr`),
        `is_calibrator` (int, 0/1).
    covariance : ndarray (N, N)
        Full statistical + systematic covariance matrix.
    """
    if not unanchored:
        raise NotImplementedError(
            "Anchored Pantheon+ configuration is not in ERSAF v1 scope per pre-reg §3.1."
        )

    # Read data table
    raw = pd.read_csv(path_data, sep=r"\s+", comment="#")
    required = {"zCMB", "m_b_corr"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(
            f"Pantheon+ data file {path_data} is missing required columns: "
            f"{sorted(missing)}. Available columns: {sorted(raw.columns)}. "
            "Verify the file is the Brout+2022 release `Pantheon+SH0ES.dat`."
        )

    is_calibrator = (
        raw["IS_CALIBRATOR"].astype(int).to_numpy()
        if "IS_CALIBRATOR" in raw.columns
        else np.zeros(len(raw), dtype=int)
    )

    df = pd.DataFrame({
        "zCMB": raw["zCMB"].astype(float).to_numpy(),
        "mu_obs": raw["m_b_corr"].astype(float).to_numpy(),
        "is_calibrator": is_calibrator,
    })

    # Read covariance. Format: first line is dimension N, followed by N*N values
    # in row-major order (whitespace-separated, one-per-line or flat).
    with open(path_covariance) as f:
        header = f.readline().strip()
        try:
            n_cov = int(header)
        except ValueError:
            raise ValueError(
                f"Pantheon+ covariance file {path_covariance} first line is "
                f"{header!r}; expected integer matrix dimension."
            )
        rest = f.read().split()
        values = np.array([float(x) for x in rest], dtype=float)

    if values.size != n_cov * n_cov:
        raise ValueError(
            f"Pantheon+ covariance file {path_covariance}: header reports "
            f"{n_cov}×{n_cov} = {n_cov*n_cov} values, but {values.size} were read."
        )
    covariance = values.reshape(n_cov, n_cov)

    if len(df) != n_cov:
        raise ValueError(
            f"Pantheon+ data row count ({len(df)}) doesn't match covariance "
            f"dimension ({n_cov}). The .dat file and .cov file must be from the "
            "same release."
        )

    return df, covariance


def load_desi_dr1_bao(path):
    """Load DESI DR1 BAO measurements (Adame et al. 2024).

    Per pre-reg §3.1 amendment, the data vector contains all twelve published
    BAO observables across the seven DR1 redshift bins. The exact per-bin
    structure (which bins contribute D_M+D_H pairs vs. a single D_V) is read
    from the materialized CSV rather than hardcoded — the pre-reg commits to
    "the twelve observables published in DR1" without committing in advance
    to a specific per-bin split.

    File layout. `path` is either:
      - a directory containing `desi_dr1_bao.csv` and `desi_dr1_bao_cov.npy`, or
      - a path to the CSV file (the .npy covariance is then loaded from
        `<csv_stem>_cov.npy` in the same directory).

    CSV columns (required, exact names):
      `bin_id` (int, 1..7)         redshift-bin identifier
      `bin_label` (str)            tracer label (e.g., "BGS", "LRG1", "Lyα")
      `z` (float)                  effective redshift z_eff for this observable
      `observable_type` (str)      one of "DM_over_rd", "DH_over_rd", "DV_over_rd"
      `value` (float)              published value
      `error` (float)              published 1σ uncertainty (diagonal sanity;
                                   the full covariance is in the .npy)

    Row order in the CSV MUST match the row/column order of the covariance
    matrix in the .npy file. The CSV row order is the canonical analysis
    ordering and is preserved through downstream consumption.

    Parameters
    ----------
    path : str or Path
        Directory or CSV file path.

    Returns
    -------
    df : pandas.DataFrame
        12 rows with the columns above.
    covariance : ndarray (12, 12)
        Full BAO covariance per Adame+2024.
    """
    path = Path(path)
    if path.is_dir():
        csv_path = path / "desi_dr1_bao.csv"
        cov_path = path / "desi_dr1_bao_cov.npy"
    else:
        csv_path = path
        cov_path = path.with_name(path.stem + "_cov.npy")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"DESI DR1 BAO CSV not found at {csv_path}. "
            "Materialize the data per pre-reg §3.1 / §11."
        )
    if not cov_path.exists():
        raise FileNotFoundError(
            f"DESI DR1 BAO covariance not found at {cov_path}. "
            "Materialize the covariance per pre-reg §3.1 / §11."
        )

    df = pd.read_csv(csv_path)

    required = {"bin_id", "bin_label", "z", "observable_type", "value", "error"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"DESI DR1 BAO CSV {csv_path} is missing required columns: "
            f"{sorted(missing)}. Available: {sorted(df.columns)}."
        )

    valid_types = {"DM_over_rd", "DH_over_rd", "DV_over_rd"}
    observed_types = set(df["observable_type"].astype(str))
    bad_types = observed_types - valid_types
    if bad_types:
        raise ValueError(
            f"DESI DR1 BAO CSV has unrecognized observable_type values: {bad_types}. "
            f"Expected one of: {sorted(valid_types)}."
        )

    # Ensure deterministic dtypes for downstream consumers
    df = df.assign(
        bin_id=df["bin_id"].astype(int),
        bin_label=df["bin_label"].astype(str),
        z=df["z"].astype(float),
        observable_type=df["observable_type"].astype(str),
        value=df["value"].astype(float),
        error=df["error"].astype(float),
    )

    covariance = np.load(cov_path)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError(
            f"DESI DR1 BAO covariance {cov_path} has shape {covariance.shape}; "
            "expected a square 2D matrix."
        )
    if covariance.shape[0] != len(df):
        raise ValueError(
            f"DESI DR1 BAO covariance shape {covariance.shape} doesn't match "
            f"CSV row count {len(df)}. The CSV and covariance must be from the "
            "same materialization."
        )

    # Sanity: published 1σ should match sqrt(diag(cov)) to ~1% (small mismatch
    # is acceptable for rounding; large mismatch indicates a materialization error).
    diag_err = np.sqrt(np.diag(covariance))
    csv_err = df["error"].to_numpy()
    rel_diff = np.abs(diag_err - csv_err) / np.maximum(csv_err, 1e-30)
    if np.any(rel_diff > 0.05):
        worst = int(np.argmax(rel_diff))
        raise ValueError(
            f"DESI DR1 BAO covariance diagonal disagrees with CSV `error` column "
            f"by more than 5% at row {worst} "
            f"(bin {df.iloc[worst]['bin_label']}, "
            f"{df.iloc[worst]['observable_type']}): "
            f"sqrt(diag) = {diag_err[worst]:.4f}, csv = {csv_err[worst]:.4f}. "
            "Verify the .csv and .npy are from the same materialization."
        )

    return df, covariance


def apply_redshift_cut(pantheon_df, z_floor=Z_FLOOR):
    """Apply §3.1 redshift cut: z > z_floor (default 0.01)."""
    mask = pantheon_df["zCMB"] > z_floor
    return pantheon_df[mask].reset_index(drop=True), mask


def build_joint_covariance(pantheon_cov, desi_cov):
    """§3.2 — block-diagonal joint covariance with zero cross-survey correlation.

    Returns a single (N+7) × (N+7) covariance matrix.
    """
    n_sn = pantheon_cov.shape[0]
    n_bao = desi_cov.shape[0]
    joint = np.zeros((n_sn + n_bao, n_sn + n_bao))
    joint[:n_sn, :n_sn] = pantheon_cov
    joint[n_sn:, n_sn:] = desi_cov
    return joint


def verify_positive_definite(matrix, threshold=1e-12):
    """§5.3 — verify joint covariance is numerically positive-definite.

    Returns the smallest eigenvalue. If below threshold, the caller
    is expected to abort the setup with a clear error.
    """
    eigenvalues = np.linalg.eigvalsh(matrix)
    return float(eigenvalues.min())


def post_fit_residual_se(joint_cov, joint_cov_cholesky_L, whitened_jacobian, n_sn):
    """§4.1 / §4.3 — Per-data-point post-fit residual standard error, GLS-propagated.

    Pre-registration §4.1 requires "the standard error is derived from the GLS-fit
    propagation of Section 3's full covariance, not from the empirical scatter
    of the binned means." This function implements that propagation via the
    standard hat-matrix correction.

    Standard regression result for generalized least squares with data
    covariance C, model prediction f(θ), and best-fit θ̂:

        r̂ = d - f(θ̂)
        Cov(r̂) = C - F (F^T C^{-1} F)^{-1} F^T

    where F = ∂f/∂θ at θ̂ is the model Jacobian.

    In whitened coordinates with C = L L^T and J_w = L^{-1} F:

        F^T C^{-1} F = J_w^T J_w
        F = L J_w
        Cov(r̂) = L L^T - L J_w (J_w^T J_w)^{-1} J_w^T L^T

    The per-data-point post-fit variance simplifies to:

        Var(r̂_i) = C_ii - F_i^T (J_w^T J_w)^{-1} F_i

    `scipy.optimize.least_squares` with method='trf' returns the Jacobian of the
    whitened residual function in `result.jac` (up to sign convention). The
    products F (J_w^T J_w)^{-1} F^T below are sign-invariant, so the raw
    `result.jac` can be passed as `whitened_jacobian` without sign correction.

    Parameters
    ----------
    joint_cov : ndarray (n_data, n_data)
        Joint data covariance C.
    joint_cov_cholesky_L : ndarray (n_data, n_data)
        Lower Cholesky factor of joint_cov, satisfying C = L L^T.
    whitened_jacobian : ndarray (n_data, n_params)
        `result.jac` from scipy.optimize.least_squares (Jacobian of the
        whitened residual function at the best fit, up to sign).
    n_sn : int
        Number of supernova data points (first n_sn rows of the data vector).

    Returns
    -------
    sn_se : ndarray (n_sn,)
        Per-SN post-fit residual standard error.
    bao_se : ndarray (n_bao,)
        Per-BAO post-fit residual standard error (returned for completeness;
        the BAO diagnostic per §4.5 uses empirical null distributions and
        does not consume these directly).
    """
    L = joint_cov_cholesky_L
    J_w = whitened_jacobian

    # Model Jacobian F = L J_w. The sign of J_w cancels in the F (J_w^T J_w)^{-1} F^T
    # quadratic form, so result.jac can be used directly without sign correction.
    F = L @ J_w

    # (J_w^T J_w)^{-1}. Use pinv to be robust against bound-active parameters
    # whose Jacobian column may be zeroed by trf at the bound.
    JtJ = J_w.T @ J_w
    JtJ_inv = np.linalg.pinv(JtJ)

    # Per-data-point hat-matrix diagonal via einsum:
    #   H_diag[i] = sum_{j,k} F[i,j] * JtJ_inv[j,k] * F[i,k]
    H_diag = np.einsum("ij,jk,ik->i", F, JtJ_inv, F)

    # Data variance diagonal
    C_diag = np.diag(joint_cov)

    # Post-fit residual variance. In exact arithmetic H_diag ≤ C_diag (the hat
    # matrix is a projection in the C-weighted inner product). Floating-point
    # rounding can produce tiny negatives or zeros that would propagate as
    # 1/σ² = inf in downstream consumers (notably the weighted PELT cost),
    # silently corrupting segmentation with NaN costs. Clip to a strict-positive
    # floor proportional to data scale: 1e-12 × C_diag is ~14 orders below
    # typical Pantheon+ SE² ≈ 0.01 mag², well below any real measurement
    # precision but strictly positive so 1/σ² stays finite.
    floor = 1e-12 * C_diag
    post_fit_var = np.maximum(C_diag - H_diag, floor)

    sn_se = np.sqrt(post_fit_var[:n_sn])
    bao_se = np.sqrt(post_fit_var[n_sn:])
    return sn_se, bao_se


# ============================================================================
# JOINT GLS FIT (§2, §7)
# ============================================================================


def predict_pantheon(z_array, params, hubble_fn, MB=0.0):
    """Predict distance modulus for each SN at its redshift."""
    return np.array([distance_modulus(z, params, hubble_fn, MB=MB) for z in z_array])


def predict_desi_bao(bao_df, params, hubble_fn):
    """Predict BAO observables (DM/rd, DH/rd, or DV/rd) at each BAO observable's redshift.

    bao_df columns: z, observable_type ∈ {"DM_over_rd", "DH_over_rd", "DV_over_rd"},
    value, error. Per pre-reg §3.1 amendment, DESI DR1 publishes a 12-observable data
    vector with five bins reporting D_M and D_H separately and two bins reporting D_V.
    """
    predictions = []
    for _, row in bao_df.iterrows():
        z = row["z"]
        obs_type = row["observable_type"]
        if obs_type == "DM_over_rd":
            predictions.append(bao_dm_over_rd(z, params, hubble_fn))
        elif obs_type == "DH_over_rd":
            predictions.append(bao_dh_over_rd(z, params, hubble_fn))
        elif obs_type == "DV_over_rd":
            predictions.append(bao_dv_over_rd(z, params, hubble_fn))
        else:
            raise ValueError(
                f"Unknown BAO observable type: {obs_type!r}. "
                f"Expected one of: DM_over_rd, DH_over_rd, DV_over_rd."
            )
    return np.array(predictions)


def predict_joint(z_sn, bao_df, params, hubble_fn):
    """Combined prediction vector: distance moduli + BAO observables."""
    MB = params.get("MB", 0.0)
    sn_pred = predict_pantheon(z_sn, params, hubble_fn, MB=MB)
    bao_pred = predict_desi_bao(bao_df, params, hubble_fn)
    return np.concatenate([sn_pred, bao_pred])


def precompute_marginalization(joint_cov, n_sn):
    """§3.1 — Precompute quantities for analytical M_B marginalization.

    For the closed-form Gaussian marginalization of the SN absolute magnitude M_B:

        χ²_SN_marg = Δμᵀ C_SN⁻¹ Δμ − (1ᵀ C_SN⁻¹ Δμ)² / (1ᵀ C_SN⁻¹ 1)

    we precompute u = L_SN⁻¹ · 1 and u_sq_norm = ||u||². In whitened
    coordinates, the marginalization is equivalent to projecting the SN
    whitened residual orthogonally to u:

        v_SN_marg = v_SN − ((v_SN · u) / u_sq_norm) · u

    so that ||v_SN_marg||² + ||v_BAO||² = χ²_SN_marg + χ²_BAO.

    Because the §3.2 joint covariance is block-diagonal, the full Cholesky
    factor L is block-diagonal: L = block_diag(L_SN, L_BAO). L_SN is
    extracted as L[:n_sn, :n_sn].

    Returns (L, L_SN, u, u_sq_norm).
    """
    L = cholesky(joint_cov, lower=True)
    L_SN = L[:n_sn, :n_sn]
    ones_sn = np.ones(n_sn)
    u = solve_triangular(L_SN, ones_sn, lower=True)
    u_sq_norm = float(u @ u)
    return L, L_SN, u, u_sq_norm


def fit_cosmology_joint(z_sn, mu_sn, bao_df, bao_obs, joint_cov, hubble_fn,
                        param_names, initial_values, bounds):
    """§2, §3.1, §5.2 — Joint GLS fit with M_B analytically marginalized.

    Minimizes χ²_SN_marg + χ²_BAO over the cosmological parameters in
    `param_names`. M_B is analytically marginalized from the SN χ² per
    pre-reg §3.1; the optimizer never sees M_B as a free parameter.
    The marginalized best-fit M̂_B is computed post-convergence and
    returned for manifest recording.

    Solver: `scipy.optimize.least_squares` with method='trf' (trust-region
    reflective), `xtol = 1e-6`, `max_nfev = 100` (literal), per pre-reg §2.1 / §5.2.

    Returns
    -------
    best_fit : dict
        Best-fit cosmological parameters by name.
    MB_best : float
        Marginalized best-fit M̂_B = (1ᵀ C_SN⁻¹ Δμ) / (1ᵀ C_SN⁻¹ 1) at the
        converged cosmology. Returns NaN if convergence failed.
    result : scipy.optimize.OptimizeResult
        The full scipy result, exposing `result.jac` (whitened Jacobian of
        the marginalized residual function, used by post_fit_residual_se).
    converged : bool
        True iff the optimizer reported success.
    """
    n_sn = len(z_sn)
    L, L_SN, u, u_sq_norm = precompute_marginalization(joint_cov, n_sn)

    initial_array = np.array([initial_values[name] for name in param_names])
    lower = np.array([bounds[name][0] for name in param_names])
    upper = np.array([bounds[name][1] for name in param_names])

    def marginalized_residual(params_array):
        """Whitened joint residual with SN-side M_B projected out.

        Squared norm equals χ²_SN_marg + χ²_BAO at M_B = 0.
        """
        params = dict(zip(param_names, params_array))
        pred_sn = predict_pantheon(z_sn, params, hubble_fn, MB=0.0)
        pred_bao = predict_desi_bao(bao_df, params, hubble_fn)
        obs = np.concatenate([mu_sn, bao_obs])
        pred = np.concatenate([pred_sn, pred_bao])
        # Whiten the joint residual: L⁻¹(obs - pred). ||x||² = (obs-pred)ᵀ C⁻¹ (obs-pred).
        whitened = solve_triangular(L, obs - pred, lower=True)
        v_sn = whitened[:n_sn]
        v_bao = whitened[n_sn:]
        # SN-side M_B marginalization: project v_sn orthogonal to u in whitened space.
        proj_coef = (v_sn @ u) / u_sq_norm
        v_sn_marg = v_sn - proj_coef * u
        return np.concatenate([v_sn_marg, v_bao])

    result = scipy.optimize.least_squares(
        marginalized_residual,
        initial_array,
        bounds=(lower, upper),
        method="trf",          # trust-region reflective; supports bounds (LM does not)
        xtol=CONVERGENCE_TOLERANCE,
        max_nfev=ITERATION_LIMIT,  # literal 100 per pre-reg §5.2 (post-amendment)
    )

    converged = bool(result.success and result.status > 0)
    best_fit = dict(zip(param_names, result.x))

    # Compute marginalized best-fit M_B for manifest recording (does not enter any test).
    if converged:
        pred_sn_at_best = predict_pantheon(z_sn, best_fit, hubble_fn, MB=0.0)
        delta_mu = mu_sn - pred_sn_at_best
        whitened_dmu_sn = solve_triangular(L_SN, delta_mu, lower=True)
        MB_best = float(u @ whitened_dmu_sn) / u_sq_norm
    else:
        MB_best = float("nan")

    return best_fit, MB_best, result, converged


# ============================================================================
# DIAGNOSTIC BATTERY (§4)
# ============================================================================


def bin_sn_residuals(z_sn, residuals_sn, sn_se_post_gls, n_bins=N_BINS):
    """§4.1 — Bin SN residuals into n_bins of equal SN count, sorted by z.

    Returns (bin_mean_residuals, bin_standard_errors, bin_z_ranges).

    Per-bin reduction:
        bin_mean[i] = (Σ_{j ∈ bin i} r_j / σ²_j) / (Σ_{j ∈ bin i} 1 / σ²_j)
        bin_se[i]   = sqrt(1 / (Σ_{j ∈ bin i} 1 / σ²_j))

    Both quantities are computed under inverse-variance weighting so that
    the bin mean is the maximum-likelihood estimate of the in-bin mean under
    the GLS-propagated per-SN standard errors and the bin SE is its proper
    error. Pre-reg §4.1: "the standard error is derived from the GLS-fit
    propagation of Section 3's full covariance, not from the empirical
    scatter of the binned means."
    """
    sort_idx = np.argsort(z_sn)
    z_sorted = z_sn[sort_idx]
    res_sorted = residuals_sn[sort_idx]
    se_sorted = sn_se_post_gls[sort_idx]

    n_per_bin = len(z_sorted) // n_bins
    bin_means = np.zeros(n_bins)
    bin_ses = np.zeros(n_bins)
    bin_z_ranges = []

    for i in range(n_bins):
        start = i * n_per_bin
        end = start + n_per_bin if i < n_bins - 1 else len(z_sorted)
        residuals_in_bin = res_sorted[start:end]
        se_in_bin = se_sorted[start:end]
        var_per_sn = se_in_bin ** 2
        inv_var = 1.0 / var_per_sn
        sum_inv_var = float(np.sum(inv_var))
        # Inverse-variance weighted mean (matches the IVW SE formula below)
        bin_means[i] = float(np.sum(residuals_in_bin * inv_var) / sum_inv_var)
        # IVW SE: var of the weighted mean = 1 / sum(1/var_per_sn)
        bin_ses[i] = float(np.sqrt(1.0 / sum_inv_var))
        bin_z_ranges.append((z_sorted[start], z_sorted[end - 1]))

    return bin_means, bin_ses, bin_z_ranges


def compute_cwt(binned_residuals):
    """§4.2 — Continuous wavelet transform with Mexican hat (DOG-2) on binned signal.

    Returns coefficients (n_scales × n_bins) and the COI mask (n_scales × n_bins, bool).
    """
    import pywt  # local import to keep dependency explicit
    scales = np.logspace(
        np.log10(CWT_SCALE_MIN), np.log10(CWT_SCALE_MAX), CWT_N_SCALES
    )
    # Symmetric extension boundary handling
    n = len(binned_residuals)
    pad = int(np.ceil(CWT_SCALE_MAX))
    extended = np.concatenate(
        [binned_residuals[pad - 1::-1], binned_residuals, binned_residuals[-1:-pad - 1:-1]]
    )
    coefficients, freqs = pywt.cwt(extended, scales, CWT_WAVELET)
    # Extract central portion corresponding to original signal
    coefficients = coefficients[:, pad:pad + n]

    # Cone of influence: at each scale, mask coefficients within the T&C 1998
    # e-folding distance from either edge. For the DOG(m=2) Mexican hat wavelet,
    # the e-folding criterion gives coi_width = scale × sqrt(m + 0.5) = scale × sqrt(2.5).
    # Per pre-reg §4.2: on a 20-bin signal with scale range 1-7, scales above ~5
    # have zero testable coefficients, and this is the acknowledged broad-feature
    # blind spot of the wavelet diagnostic on the locked signal length (§9.6).
    coi_mask = np.zeros_like(coefficients, dtype=bool)
    for i, scale in enumerate(scales):
        coi_width = int(np.ceil(scale * np.sqrt(2.5)))
        # When 2 × coi_width ≥ n the two edge masks overlap and the entire row
        # is masked; that scale contributes zero testable coefficients, which is
        # the intended T&C behavior.
        coi_mask[i, :min(coi_width, n)] = True
        coi_mask[i, max(0, n - coi_width):] = True

    return coefficients, coi_mask, scales


def compute_pelt_change_count(binned_residuals, binned_ses):
    """§4.3 — PELT change-point detection with weighted Gaussian mean-shift cost.

    Implements pre-reg §4.3:
        "Gaussian mean-shift likelihood. The cost function uses per-bin
         standard errors derived from the GLS-fit propagation of Section 3's
         full covariance, not the empirical scatter of the binned means."

    Per-segment cost (weighted Gaussian, σᵢ² known from GLS-propagated SE):

        C(start, end) = Σ_{i=start}^{end-1} (r_i - μ̂_segment)² / σ²_i

    where μ̂_segment = (Σ rᵢ/σ²ᵢ) / (Σ 1/σ²ᵢ) is the IVW segment mean.
    Implemented via cumulative-sum precomputation so each segment cost
    evaluation is O(1) rather than O(segment length).

    BIC penalty: log(n). With the weighted cost (per-bin variance folded
    into the likelihood), adding one change point adds one new segment-mean
    parameter; the BIC contribution per added parameter is log(n). The
    earlier `σ² × log(n)` form was incorrect twice over — it used empirical
    scatter (forbidden by §4.3) AND double-counted σ relative to the
    weighted cost.

    Returns
    -------
    n_change_points : int
        Number of detected change points (the test statistic per §4.3).
    change_point_locations : list[int]
        Bin-index locations of detected change points (descriptive only,
        not used in the significance test per §4.3).
    """
    import ruptures as rpt
    n = len(binned_residuals)

    class _WeightedGaussianMeanShiftCost(rpt.base.BaseCost):
        """Custom PELT cost: weighted Gaussian mean-shift with known per-bin σ²."""

        model = "weighted_gaussian_mean_shift"
        min_size = PELT_MIN_SEGMENT

        def fit(self, signal):
            # signal shape: (n, 2). signal[:, 0] = residuals, signal[:, 1] = variances.
            residuals = signal[:, 0]
            variances = signal[:, 1]
            inv_var = 1.0 / variances
            r_iv = residuals * inv_var
            r_sq_iv = residuals ** 2 * inv_var
            # Cumulative sums for O(1) segment cost evaluation
            self._cum_iv = np.concatenate([[0.0], np.cumsum(inv_var)])
            self._cum_riv = np.concatenate([[0.0], np.cumsum(r_iv)])
            self._cum_rriv = np.concatenate([[0.0], np.cumsum(r_sq_iv)])
            return self

        def error(self, start, end):
            # cost = Σ r²/σ² − (Σ r/σ²)² / (Σ 1/σ²)
            S_iv = self._cum_iv[end] - self._cum_iv[start]
            S_riv = self._cum_riv[end] - self._cum_riv[start]
            S_rriv = self._cum_rriv[end] - self._cum_rriv[start]
            if S_iv <= 0:
                return 0.0
            cost = S_rriv - (S_riv * S_riv) / S_iv
            # Belt-and-suspenders: an inf or NaN segment cost (e.g., from a
            # σ² = 0 upstream slipping past the post_fit_residual_se floor)
            # would silently corrupt PELT's segmentation. Return +inf in those
            # cases so the optimizer is forced to avoid such segments.
            if not np.isfinite(cost):
                return float("inf")
            return float(cost)

    signal = np.column_stack([binned_residuals, binned_ses ** 2])
    cost = _WeightedGaussianMeanShiftCost().fit(signal)
    algo = rpt.Pelt(custom_cost=cost, min_size=PELT_MIN_SEGMENT).fit(signal)
    penalty = float(np.log(n))
    change_points = algo.predict(pen=penalty)
    # Remove the implicit terminal change-point at n
    change_points = [cp for cp in change_points if cp != n]
    return len(change_points), change_points


def compute_acf(binned_residuals, lags=ACF_LAGS):
    """§4.4 — Pearson autocorrelation at specified lags, biased estimator.

    Returns array of ACF values at each lag.
    """
    from statsmodels.tsa.stattools import acf
    n_lags = max(lags)
    # Verify statsmodels API at lock commit; the `adjusted` parameter name and
    # default may differ across versions.
    acf_values = acf(binned_residuals, nlags=n_lags, adjusted=ACF_ADJUSTED, fft=False)
    return np.array([acf_values[lag] for lag in lags])


def compute_diagnostic_battery(z_sn, sn_residuals, sn_se, bao_residuals):
    """Compute all four diagnostic families on a single residual realization.

    Returns a dict containing:
        wavelet_coefs: (n_scales, n_bins) array
        wavelet_coi_mask: (n_scales, n_bins) bool array
        wavelet_scales: (n_scales,) array
        pelt_count: int (number of change-points)
        pelt_locations: list of int (descriptive only, not used in test)
        acf_values: (5,) array
        bao_residuals: (7,) array
        bin_means: (n_bins,) array
        bin_ses: (n_bins,) array
        bin_z_ranges: list of (z_lo, z_hi) tuples
    """
    bin_means, bin_ses, bin_z_ranges = bin_sn_residuals(z_sn, sn_residuals, sn_se)
    wavelet_coefs, wavelet_coi_mask, wavelet_scales = compute_cwt(bin_means)
    pelt_count, pelt_locs = compute_pelt_change_count(bin_means, bin_ses)
    acf_values = compute_acf(bin_means)
    return {
        "wavelet_coefs": wavelet_coefs,
        "wavelet_coi_mask": wavelet_coi_mask,
        "wavelet_scales": wavelet_scales,
        "pelt_count": pelt_count,
        "pelt_locations": pelt_locs,
        "acf_values": acf_values,
        "bao_residuals": bao_residuals,
        "bin_means": bin_means,
        "bin_ses": bin_ses,
        "bin_z_ranges": bin_z_ranges,
    }


# ============================================================================
# MULTIPLE-TESTING CORRECTION AND VERDICT (§6, §7)
# ============================================================================


def within_diagnostic_bonferroni(p_values_dict, alpha=ALPHA):
    """§6.1 — Apply within-diagnostic Bonferroni correction.

    p_values_dict: keys are diagnostic family names, values are arrays of p-values.
        Wavelet p_values are flattened across (scale, position) coefficients
        outside the COI.
        PELT is a single p-value (scalar or length-1 array).
        ACF is length-5.
        BAO is length-7.

    Returns a dict with per-diagnostic firing flags and the (test-index,
    p-value, threshold) for each significant test.
    """
    results = {}
    for diagnostic_name, p_array in p_values_dict.items():
        p_array = np.atleast_1d(p_array)
        n_tests = len(p_array)
        threshold = alpha / n_tests if n_tests > 0 else alpha
        significant_idx = np.where(p_array <= threshold)[0]
        results[diagnostic_name] = {
            "n_tests": n_tests,
            "threshold": threshold,
            "n_significant": len(significant_idx),
            "fires": len(significant_idx) > 0,
            "significant_test_indices": significant_idx.tolist(),
            "significant_pvalues": p_array[significant_idx].tolist(),
        }
    return results


def cross_diagnostic_verdict(within_diagnostic_results, k=COMBINATION_RULE_K):
    """§6.2 — Cross-diagnostic 2-of-4 combination rule.

    Returns (positive_verdict_bool, list_of_firing_diagnostics).
    """
    firing = [name for name, r in within_diagnostic_results.items() if r["fires"]]
    positive = len(firing) >= k
    return positive, firing


def benjamini_hochberg_within_diagnostic(p_values_dict, q=ALPHA):
    """§6.3 — Apply BH FDR correction within each diagnostic family for secondary disclosure."""
    from scipy.stats import false_discovery_control
    results = {}
    for diagnostic_name, p_array in p_values_dict.items():
        p_array = np.atleast_1d(p_array)
        if len(p_array) == 0:
            results[diagnostic_name] = {"n_significant": 0, "fires": False}
            continue
        adjusted = false_discovery_control(p_array, method="bh")
        significant = np.where(adjusted <= q)[0]
        results[diagnostic_name] = {
            "n_significant": len(significant),
            "fires": len(significant) > 0,
            "significant_test_indices": significant.tolist(),
        }
    return results


# ============================================================================
# MOCK GENERATION (§5)
# ============================================================================


def generate_mock_realization(mock_idx, L_cholesky, n_total, sub_seed):
    """§5.2 — Generate a single mock realization.

    Returns z_i ~ N(0, I) of length n_total, used by the caller to construct
    mock_residuals = L @ z_i.

    Per §5.1, sub_seed comes from SeedSequence(MASTER_SEED).spawn(N_MOCKS)[mock_idx].
    """
    rng = np.random.default_rng(sub_seed)
    z = rng.standard_normal(n_total)
    return z


def run_mocks_for_baseline(baseline_name, hubble_fn, param_names, initial_values, bounds,
                            z_sn, bao_df, joint_cov, L_cholesky, best_fit_observed):
    """§5, §7 — Run N_MOCKS mock realizations for a given baseline cosmology.

    Returns a dict of mock-statistic arrays for downstream significance computation.
    """
    n_total = joint_cov.shape[0]
    n_sn = len(z_sn)

    # §5.1 — Deterministic sub-seed generation
    seed_seq = np.random.SeedSequence(MASTER_SEED)
    sub_seeds = seed_seq.spawn(N_MOCKS)

    # Per-mock storage
    mock_wavelet = []   # list of flattened coefficient arrays (outside COI)
    mock_pelt_count = []
    mock_acf = []
    mock_bao = []
    convergence_failures = 0

    # Compute observed best-fit predictions
    obs_pred = predict_joint(z_sn, bao_df, best_fit_observed, hubble_fn)
    mu_obs_sn = obs_pred[:n_sn]
    bao_obs = obs_pred[n_sn:]

    for i in range(N_MOCKS):
        z = generate_mock_realization(i, L_cholesky, n_total, sub_seeds[i])
        mock_residuals = L_cholesky @ z
        mock_obs = obs_pred + mock_residuals
        mock_mu_sn = mock_obs[:n_sn]
        mock_bao_obs = mock_obs[n_sn:]

        # Refit baseline cosmology to mock observations. M_B is analytically
        # marginalized inside fit_cosmology_joint (§3.1); mock_MB is the
        # closed-form best-fit M̂_B for this mock, kept for diagnostic logging
        # but not used in any test or downstream computation.
        try:
            mock_fit, mock_MB, mock_result, converged = fit_cosmology_joint(
                z_sn, mock_mu_sn, bao_df, mock_bao_obs, joint_cov, hubble_fn,
                param_names, initial_values, bounds,
            )
            if not converged:
                convergence_failures += 1
                continue
        except Exception:
            convergence_failures += 1
            continue

        # Compute mock-fit residuals. Apply the marginalized M̂_B to the SN
        # prediction so the post-fit SN residual is what the diagnostic battery
        # consumes (μ_obs − μ_pred(θ̂) − M̂_B), matching the data the fit actually
        # describes. BAO residuals are independent of M_B.
        mock_pred = predict_joint(z_sn, bao_df, mock_fit, hubble_fn)
        sn_residuals = mock_mu_sn - mock_pred[:n_sn] - mock_MB
        bao_residuals = mock_bao_obs - mock_pred[n_sn:]

        # §4.1 — Per-bin SE derives from GLS-fit propagation of the joint covariance.
        # Computed via the hat-matrix correction; see post_fit_residual_se.
        sn_se, _ = post_fit_residual_se(joint_cov, L_cholesky, mock_result.jac, n_sn)

        diagnostics = compute_diagnostic_battery(z_sn, sn_residuals, sn_se, bao_residuals)

        # Store
        coefs_outside_coi = diagnostics["wavelet_coefs"][~diagnostics["wavelet_coi_mask"]]
        mock_wavelet.append(coefs_outside_coi)
        mock_pelt_count.append(diagnostics["pelt_count"])
        mock_acf.append(diagnostics["acf_values"])
        mock_bao.append(diagnostics["bao_residuals"])

        if (i + 1) % 500 == 0:
            print(f"    [{baseline_name}] mock {i+1}/{N_MOCKS} "
                  f"(failures so far: {convergence_failures})")

    failure_rate = convergence_failures / N_MOCKS
    print(f"  {baseline_name}: {N_MOCKS - convergence_failures} successful mocks, "
          f"{convergence_failures} failures ({100*failure_rate:.2f}%)")
    if failure_rate > 0.01:
        print(f"  WARNING: failure rate {100*failure_rate:.2f}% exceeds 1% pause threshold (§5.4).")

    return {
        "wavelet": np.array(mock_wavelet),         # (N_successful, N_coefs_outside_coi)
        "pelt_count": np.array(mock_pelt_count),   # (N_successful,)
        "acf": np.array(mock_acf),                 # (N_successful, 5)
        "bao": np.array(mock_bao),                 # (N_successful, 7)
        "failure_rate": failure_rate,
    }


# ============================================================================
# MODES
# ============================================================================


def cmd_setup(args):
    """§11 — Setup mode: materialize data, compute hashes, fit baselines, emit TBDs.

    Per pre-reg §10 (Pre-lock integrity), no diagnostic statistics are computed
    on observed or mock data during setup. The setup phase produces the lock
    manifest values that fill the §11 TBD placeholders; the diagnostic battery
    runs only during `run` mode after lock commit.

    Outputs (all written under args.output_dir):
      library_versions.json       Pinned environment manifest.
      joint_data_sha256.txt       Per-file SHA-256 hashes of materialized data
                                  plus the constructed joint covariance hash.
      ersaf_setup_manifest.json   Full structured manifest with all §11 TBD
                                  values in copy-pasteable JSON form,
                                  including per-bin DESI observable split.
    """
    print("=" * 72)
    print("ERSAF — SETUP MODE")
    print("=" * 72)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # === Step 1: Load Pantheon+ ===
    print("\nStep 1: Load Pantheon+ data and covariance (unanchored).")
    try:
        pantheon_df_full, pantheon_cov_full = load_pantheon_plus(
            args.pantheon_data, args.pantheon_cov, unanchored=True,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        sys.exit(10)
    n_full = len(pantheon_df_full)
    print(f"  Loaded {n_full} Pantheon+ SNe, covariance shape {pantheon_cov_full.shape}.")

    # === Step 2: Apply z > 0.01 cut ===
    print(f"\nStep 2: Apply redshift cut z > {Z_FLOOR}.")
    pantheon_df, retained_mask = apply_redshift_cut(pantheon_df_full)
    n_sn = len(pantheon_df)
    retained_idx = (
        np.where(retained_mask.to_numpy())[0]
        if hasattr(retained_mask, "to_numpy")
        else np.where(np.asarray(retained_mask))[0]
    )
    pantheon_cov = pantheon_cov_full[np.ix_(retained_idx, retained_idx)]
    print(f"  Retained {n_sn} of {n_full} SNe.")

    # === Step 3: Load DESI DR1 BAO ===
    print("\nStep 3: Load DESI DR1 BAO data.")
    try:
        bao_df, bao_cov = load_desi_dr1_bao(args.desi_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        sys.exit(10)
    n_bao = len(bao_df)
    print(f"  Loaded {n_bao} BAO observables, covariance shape {bao_cov.shape}.")
    assert n_bao == 12, (
        f"Pre-reg §3.1 (post-amendment) locks the DESI DR1 BAO observable count at 12; "
        f"loaded {n_bao}. Lock-version drift detected."
    )

    # Record the per-bin observable split for the manifest. The comprehensive
    # review (#96) will verify that this matches Adame+2024 Table 1 — i.e., not
    # just "12 observables total" but "the right 12, with the right per-bin
    # D_M/D_H/D_V split at the right z_eff values."
    desi_split = {}
    for bid in sorted(int(x) for x in bao_df["bin_id"].unique()):
        bin_rows = bao_df[bao_df["bin_id"] == bid]
        desi_split[bid] = {
            "label": str(bin_rows["bin_label"].iloc[0]),
            "z_eff": float(bin_rows["z"].iloc[0]),
            "observables": sorted(bin_rows["observable_type"].astype(str).tolist()),
        }
    print("  DESI per-bin observable split:")
    for bid, info in desi_split.items():
        obs_str = "+".join(info["observables"])
        print(f"    bin {bid} ({info['label']}, z_eff={info['z_eff']:.3f}): {obs_str}")

    # === Step 4: Build joint covariance and verify positive-definiteness ===
    print("\nStep 4: Build joint covariance and verify positive-definiteness.")
    joint_cov = build_joint_covariance(pantheon_cov, bao_cov)
    min_eig = verify_positive_definite(joint_cov)
    print(f"  Joint covariance shape: {joint_cov.shape}.")
    print(f"  Smallest eigenvalue:    {min_eig:.6e}.")
    if min_eig < 1e-12:
        print(
            "  ERROR: joint covariance is not numerically positive-definite. "
            "Aborting per §5.3.",
            file=sys.stderr,
        )
        sys.exit(11)
    print("  Positive-definite check: PASS.")

    # === Step 5: Compute Cholesky ===
    print("\nStep 5: Compute Cholesky factor.")
    L_chol = cholesky(joint_cov, lower=True)
    print(f"  Cholesky factor computed (lower triangular, shape {L_chol.shape}).")

    # === Step 6: Initial joint fits per baseline ===
    print("\nStep 6: Initial joint fits for ΛCDM / wCDM / w0wa CDM.")
    print("        (Diagnostics are NOT computed here per pre-reg §10.)")
    z_sn = pantheon_df["zCMB"].to_numpy()
    mu_sn = pantheon_df["mu_obs"].to_numpy()
    bao_obs = bao_df["value"].to_numpy()

    initial_fits = {}
    for name, hubble_fn, param_names, initial, bounds in [
        ("LambdaCDM", hubble_function_lambda_cdm,
         LAMBDA_CDM_PARAM_NAMES, LAMBDA_CDM_INITIAL, LAMBDA_CDM_BOUNDS),
        ("wCDM", hubble_function_wcdm,
         WCDM_PARAM_NAMES, WCDM_INITIAL, WCDM_BOUNDS),
        ("w0waCDM", hubble_function_w0wa,
         W0WA_PARAM_NAMES, W0WA_INITIAL, W0WA_BOUNDS),
    ]:
        best_fit, MB_best, _result, converged = fit_cosmology_joint(
            z_sn, mu_sn, bao_df, bao_obs, joint_cov, hubble_fn,
            param_names, initial, bounds,
        )
        if not converged:
            print(
                f"  ERROR: {name} initial fit did not converge. Cannot proceed to lock.",
                file=sys.stderr,
            )
            sys.exit(12)
        initial_fits[name] = {
            "params": {k: float(v) for k, v in best_fit.items()},
            "MB_marginalized": float(MB_best),
        }
        fit_str = ", ".join(f"{k}={v:.4f}" for k, v in best_fit.items())
        print(f"  {name:>10s}: {fit_str}; M̂_B = {MB_best:+.6f}")

    # === Step 7: SHA-256 hashes ===
    print("\nStep 7: Compute SHA-256 hashes of materialized data files.")
    # Resolve DESI file paths (directory vs file)
    desi_arg = Path(args.desi_path)
    if desi_arg.is_dir():
        desi_csv_path = str(desi_arg / "desi_dr1_bao.csv")
        desi_cov_path = str(desi_arg / "desi_dr1_bao_cov.npy")
    else:
        desi_csv_path = str(desi_arg)
        desi_cov_path = str(desi_arg.with_name(desi_arg.stem + "_cov.npy"))

    # H7: normalize all manifest paths to forward-slash, no leading "./" prefix.
    # Path inputs from argparse may have ".\\" on Windows or "./" on POSIX or
    # neither, depending on how the user invoked the command. The manifest is
    # both a human-readable artifact and a reproducibility input, so paths are
    # canonicalized here for cross-platform stability.
    def _norm_manifest_path(p):
        s = str(p).replace("\\", "/")
        while s.startswith("./"):
            s = s[2:]
        return s
    data_files = {
        "pantheon_data": _norm_manifest_path(args.pantheon_data),
        "pantheon_cov":  _norm_manifest_path(args.pantheon_cov),
        "desi_csv":      _norm_manifest_path(desi_csv_path),
        "desi_cov":      _norm_manifest_path(desi_cov_path),
    }
    file_hashes = {}
    for tag, file_path in data_files.items():
        if not Path(file_path).exists():
            print(f"  WARNING: {tag} not found at {file_path}; skipping hash.")
            file_hashes[tag] = None
            continue
        h = sha256_of_file(file_path)
        file_hashes[tag] = h
        print(f"  {tag:>14s}: {h}")

    # Hash the constructed joint covariance (independent of file format quirks)
    joint_cov_hash = hashlib.sha256(np.ascontiguousarray(joint_cov).tobytes()).hexdigest()
    print(f"  {'joint_cov':>14s}: {joint_cov_hash}")

    # === Step 8: Library versions ===
    print("\nStep 8: Library version manifest.")
    import platform
    import scipy as _scipy_mod
    library_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": _scipy_mod.__version__,
        "pandas": pd.__version__,
    }
    for mod_name in ("statsmodels", "ruptures", "pywt"):
        try:
            mod = __import__(mod_name)
            library_versions[mod_name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            library_versions[mod_name] = "not installed"
    library_versions["script_solver"] = "scipy.optimize.least_squares method=trf"
    library_versions["multitesting_impl"] = "scipy.stats.false_discovery_control method=bh"
    for lib, ver in library_versions.items():
        print(f"  {lib:>20s}: {ver}")

    # === Step 9: Write manifest files ===
    print("\nStep 9: Write manifest files.")

    # library_versions.json
    lv_path = out_dir / "library_versions.json"
    with open(lv_path, "w") as f:
        json.dump(library_versions, f, indent=2)
    print(f"  Wrote {lv_path}")

    # joint_data_sha256.txt (sha256sum-compatible format)
    hashes_path = out_dir / "joint_data_sha256.txt"
    with open(hashes_path, "w") as f:
        for tag, h in file_hashes.items():
            if h is not None:
                f.write(f"{h}  {data_files[tag]}\n")
        f.write(f"{joint_cov_hash}  joint_covariance_constructed\n")
    print(f"  Wrote {hashes_path}")

    # Full structured setup manifest with §11 TBD values
    tbd_manifest = {
        "lock_commit": "TBD (fill after git commit, with the resulting commit SHA)",
        "pinned_pantheon_release": {
            "release_citation": "Brout et al. 2022 (Pantheon+); GitHub PantheonPlusSH0ES/DataRelease",
            "data_path": data_files["pantheon_data"],
            "cov_path": data_files["pantheon_cov"],
            "data_sha256": file_hashes.get("pantheon_data"),
            "cov_sha256": file_hashes.get("pantheon_cov"),
            "configuration": "unanchored",
        },
        "pinned_desi_dr1_release": {
            "release_citation": "Adame et al. 2024 (DESI DR1 BAO)",
            "csv_path": data_files["desi_csv"],
            "cov_path": data_files["desi_cov"],
            "csv_sha256": file_hashes.get("desi_csv"),
            "cov_sha256": file_hashes.get("desi_cov"),
            "observable_count": n_bao,
            "observable_split": desi_split,
        },
        "n_post_cut": int(n_sn),
        "joint_covariance": {
            "dimensions": [int(joint_cov.shape[0]), int(joint_cov.shape[1])],
            "sha256_constructed": joint_cov_hash,
            "smallest_eigenvalue": float(min_eig),
            "positive_definite": True,
        },
        "marginalized_MB_per_baseline": {
            name: fit["MB_marginalized"] for name, fit in initial_fits.items()
        },
        "initial_fits": initial_fits,
        "reproducibility_manifest": library_versions,
    }
    tbd_path = out_dir / "ersaf_setup_manifest.json"
    with open(tbd_path, "w") as f:
        json.dump(tbd_manifest, f, indent=2, default=str)
    print(f"  Wrote {tbd_path}")

    # === Final: human-readable §11 TBD summary ===
    print()
    print("=" * 72)
    print("SETUP COMPLETE — values to fill into PRE_REGISTRATION_ERSAF_v1.md §11")
    print("=" * 72)
    print()
    print("Human-readable form:")
    print(f"  Pinned Pantheon+ release: Brout et al. 2022")
    print(f"    data SHA-256: {file_hashes.get('pantheon_data', 'N/A')}")
    print(f"    cov  SHA-256: {file_hashes.get('pantheon_cov',  'N/A')}")
    print(f"  Pinned DESI DR1 release:  Adame et al. 2024")
    print(f"    csv SHA-256:  {file_hashes.get('desi_csv', 'N/A')}")
    print(f"    cov SHA-256:  {file_hashes.get('desi_cov', 'N/A')}")
    print(f"  N_post-cut: {n_sn}")
    print(f"  Joint covariance dimensions: {joint_cov.shape[0]} × {joint_cov.shape[1]}")
    print(f"  Joint covariance SHA-256:    {joint_cov_hash}")
    print(f"  Joint covariance smallest eigenvalue: {min_eig:.6e}")
    print(f"  Marginalized M̂_B per baseline:")
    for name, fit in initial_fits.items():
        print(f"    {name:>10s}: {fit['MB_marginalized']:+.6f}")
    print()
    print(f"Structured form (ersaf_setup_manifest.json, copy-pasteable):")
    print(json.dumps(tbd_manifest, indent=2, default=str))
    print()
    print("After lock commit, run `run` mode to execute the full analysis.")


def _compute_pvalues_from_mocks(obs_diagnostics, mock_summary, n_acf_lags, n_bao):
    """Per-test two-sided empirical p-values for one baseline (§4.2–§4.5).

    Returns a dict keyed by diagnostic family name, with values arrays of
    p-values ready for within_diagnostic_bonferroni / benjamini_hochberg.
    """
    # Wavelet: per-coefficient p-value for each coefficient outside the COI.
    # Observed coefficients outside COI; the mock array is (N_successful, N_coef_outside_coi).
    obs_wav = obs_diagnostics["wavelet_coefs"][~obs_diagnostics["wavelet_coi_mask"]]
    mock_wav = mock_summary["wavelet"]
    if mock_wav.size > 0 and obs_wav.size > 0:
        wavelet_pvalues = np.array([
            two_sided_empirical_pvalue(obs_wav[j], mock_wav[:, j])
            for j in range(len(obs_wav))
        ])
    else:
        wavelet_pvalues = np.array([])

    # PELT: single test on the change-point count
    pelt_pvalue = two_sided_empirical_pvalue(
        obs_diagnostics["pelt_count"], mock_summary["pelt_count"]
    )

    # ACF: per-lag (lags 1..5 by default)
    acf_pvalues = np.array([
        two_sided_empirical_pvalue(
            obs_diagnostics["acf_values"][k], mock_summary["acf"][:, k]
        )
        for k in range(n_acf_lags)
    ])

    # BAO: per-point (7 measurements)
    bao_pvalues = np.array([
        two_sided_empirical_pvalue(
            obs_diagnostics["bao_residuals"][k], mock_summary["bao"][:, k]
        )
        for k in range(n_bao)
    ])

    return {
        "wavelet": wavelet_pvalues,
        "pelt": np.array([pelt_pvalue]),
        "acf": acf_pvalues,
        "bao": bao_pvalues,
    }


def _serialize_baseline_for_json(baseline_record):
    """Convert a baseline_results entry into JSON-safe nested dicts."""
    def _array_to_list(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return float(x)
        if isinstance(x, set):
            return sorted(x)
        return x

    def _walk(obj):
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_walk(v) for v in obj]
        return _array_to_list(obj)

    return {
        "best_fit": {k: float(v) for k, v in baseline_record["obs_fit"].items()},
        "MB_best_fit": float(baseline_record["obs_MB"]),
        "positive_verdict": bool(baseline_record["positive_verdict"]),
        "firing_families": sorted(baseline_record["firing_families"]),
        "p_values": _walk(baseline_record["p_values"]),
        "bonferroni": _walk(baseline_record["bonferroni"]),
        "bh": _walk(baseline_record["bh"]),
        "mock_convergence_failure_rate": float(baseline_record["mock_summary"]["failure_rate"]),
    }


def _save_baseline_arrays(out_dir, baseline_name, baseline_record):
    """Persist per-baseline raw arrays for inspection and downstream tooling.

    Saves observed diagnostic outputs and the full mock distributions in
    a single .npz per baseline. Bin-z-ranges are saved as an ndarray for
    portability.
    """
    obs = baseline_record["obs_diagnostics"]
    mock = baseline_record["mock_summary"]
    np.savez(
        out_dir / f"ersaf_{baseline_name}_arrays.npz",
        # Observed
        obs_wavelet_coefs=obs["wavelet_coefs"],
        obs_wavelet_coi_mask=obs["wavelet_coi_mask"],
        obs_wavelet_scales=obs["wavelet_scales"],
        obs_pelt_count=np.array(obs["pelt_count"]),
        obs_pelt_locations=np.array(obs["pelt_locations"], dtype=object),
        obs_acf_values=obs["acf_values"],
        obs_bao_residuals=obs["bao_residuals"],
        obs_bin_means=obs["bin_means"],
        obs_bin_ses=obs["bin_ses"],
        obs_bin_z_ranges=np.array(obs["bin_z_ranges"]),
        # Mocks
        mock_wavelet=mock["wavelet"],
        mock_pelt_count=mock["pelt_count"],
        mock_acf=mock["acf"],
        mock_bao=mock["bao"],
        mock_failure_rate=np.array(mock["failure_rate"]),
    )


def cmd_run(args):
    """§5–§7 — Run mode: full analysis pipeline.

    Implements the locked methodology end-to-end:
      1. Load observed Pantheon+ + DESI DR1 data and joint covariance.
      2. Verify joint covariance is positive-definite; compute Cholesky once.
      3. For each baseline cosmology (ΛCDM, wCDM, w₀wₐ CDM):
           a. Joint GLS fit with M_B analytically marginalized.
           b. Compute observed residuals (μ_obs − μ_pred − M̂_B, BAO_obs − BAO_pred).
           c. Compute per-SN post-fit SE via hat-matrix correction.
           d. Compute observed diagnostic battery (wavelet, PELT, ACF, BAO).
           e. Generate N_MOCKS covariance-aware mock realizations and compute
              the same diagnostics on each (with per-mock refit).
           f. Compute two-sided empirical p-values per test.
           g. Apply within-diagnostic Bonferroni (primary FWER).
           h. Apply BH FDR (secondary disclosure).
           i. Determine which diagnostic families fire under the primary FWER.
      4. Cross-diagnostic 2-of-4 verdict per baseline.
      5. Combined positive-verdict criterion per §7.7: ΛCDM positive AND
         every ΛCDM-firing family also fires under wCDM and w₀wₐ CDM.
      6. Persist outputs (JSON summary + per-baseline .npz arrays).
    """
    print("=" * 72)
    print("ERSAF — RUN MODE")
    print("=" * 72)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # === Step 1: Load and verify ===
    print("\nStep 1: Load observed data and build joint covariance.")

    # Loaders raise NotImplementedError until setup-time path / format wiring.
    # When that happens, surface a clear pointer to setup mode rather than a
    # bare traceback.
    try:
        pantheon_df, pantheon_cov = load_pantheon_plus(
            args.pantheon_data, args.pantheon_cov
        )
        bao_df, bao_cov = load_desi_dr1_bao(args.desi_path)
    except NotImplementedError as exc:
        print(f"\n  ERROR: data loader not implemented: {exc}", file=sys.stderr)
        print(
            "  Implement load_pantheon_plus() and load_desi_dr1_bao() against "
            "the materialized data file layout, then re-run.",
            file=sys.stderr,
        )
        sys.exit(10)

    # Pre-reg §3.1 (post-amendment) locks the DESI DR1 BAO observable count at 12,
    # corresponding to seven redshift bins with five contributing both D_M/r_d and
    # D_H/r_d separately and two contributing a single observable (D_V/r_d or
    # equivalent). If a future release update changes the count, the pre-registered
    # analysis structure has drifted from the locked methodology; fail loud rather
    # than silently adapting.
    assert len(bao_df) == 12, (
        f"Pre-reg §3.1 locks the DESI DR1 BAO observable count at 12; "
        f"loaded {len(bao_df)} observables. Lock-version drift detected. "
        "Verify the BAO data file matches the locked release."
    )

    # §3.1 — Redshift cut on the SN sample. Slice the SN covariance to the
    # retained rows/columns so the joint covariance is consistent with the cut.
    pantheon_full = pantheon_df.copy()
    pantheon_df, retained_mask = apply_redshift_cut(pantheon_full)
    n_sn = len(pantheon_df)
    retained_idx = np.where(retained_mask.to_numpy())[0] if hasattr(retained_mask, "to_numpy") \
        else np.where(np.asarray(retained_mask))[0]
    pantheon_cov_cut = pantheon_cov[np.ix_(retained_idx, retained_idx)]
    print(f"  Pantheon+ retained: {n_sn} of {len(pantheon_full)} SNe after z > {Z_FLOOR} cut.")
    print(f"  DESI DR1 BAO points: {len(bao_df)}")

    joint_cov = build_joint_covariance(pantheon_cov_cut, bao_cov)
    min_eig = verify_positive_definite(joint_cov)
    print(f"  Joint covariance min eigenvalue: {min_eig:.3e}")
    if min_eig < 1e-12:
        print(
            "  ERROR: joint covariance is not numerically positive-definite. "
            "Aborting per §5.3.",
            file=sys.stderr,
        )
        sys.exit(11)

    # Cholesky factor reused across all mocks per §5.2.
    L_cholesky = cholesky(joint_cov, lower=True)

    z_sn = pantheon_df["zCMB"].to_numpy()
    mu_sn = pantheon_df["mu_obs"].to_numpy()
    bao_obs = bao_df["value"].to_numpy()

    # === Step 2: Per-baseline analysis ===
    baselines = [
        ("LambdaCDM", hubble_function_lambda_cdm, LAMBDA_CDM_PARAM_NAMES,
         LAMBDA_CDM_INITIAL, LAMBDA_CDM_BOUNDS),
        ("wCDM", hubble_function_wcdm, WCDM_PARAM_NAMES,
         WCDM_INITIAL, WCDM_BOUNDS),
        ("w0waCDM", hubble_function_w0wa, W0WA_PARAM_NAMES,
         W0WA_INITIAL, W0WA_BOUNDS),
    ]

    baseline_results = {}
    for name, hubble_fn, param_names, initial, bounds in baselines:
        print(f"\n=== Baseline: {name} ===")
        t_start = time.time()

        # 2a — Observed joint GLS fit (M_B analytically marginalized internally)
        obs_fit, obs_MB, obs_result, obs_converged = fit_cosmology_joint(
            z_sn, mu_sn, bao_df, bao_obs, joint_cov, hubble_fn,
            param_names, initial, bounds,
        )
        if not obs_converged:
            print(
                f"  ERROR: observed fit did not converge for {name}. Aborting.",
                file=sys.stderr,
            )
            sys.exit(12)
        print(f"  Observed best-fit cosmological parameters: {obs_fit}")
        print(f"  Observed M̂_B (marginalized): {obs_MB:.6f}")

        # 2b — Observed residuals. The SN residual subtracts the marginalized
        # M̂_B so the signal consumed by the diagnostic battery matches what
        # the fit actually describes (μ_obs − μ_pred(θ̂) − M̂_B).
        obs_pred = predict_joint(z_sn, bao_df, obs_fit, hubble_fn)
        obs_sn_residuals = mu_sn - obs_pred[:n_sn] - obs_MB
        obs_bao_residuals = bao_obs - obs_pred[n_sn:]

        # 2c — Per-SN post-fit SE via hat-matrix correction (§4.1)
        obs_sn_se, _obs_bao_se = post_fit_residual_se(
            joint_cov, L_cholesky, obs_result.jac, n_sn
        )

        # 2d — Observed diagnostic battery
        obs_diagnostics = compute_diagnostic_battery(
            z_sn, obs_sn_residuals, obs_sn_se, obs_bao_residuals
        )
        n_coef_outside_coi = int((~obs_diagnostics["wavelet_coi_mask"]).sum())
        print(
            f"  Observed diagnostics: PELT count={obs_diagnostics['pelt_count']}, "
            f"wavelet coefs outside COI={n_coef_outside_coi}, "
            f"ACF lags evaluated={len(obs_diagnostics['acf_values'])}, "
            f"BAO observables={len(obs_diagnostics['bao_residuals'])}"
        )

        # 2e — Mocks
        print(f"  Generating {N_MOCKS} mocks under {name} baseline...")
        mock_summary = run_mocks_for_baseline(
            name, hubble_fn, param_names, initial, bounds,
            z_sn, bao_df, joint_cov, L_cholesky, obs_fit,
        )

        # 2f — Per-test two-sided empirical p-values
        p_values = _compute_pvalues_from_mocks(
            obs_diagnostics, mock_summary,
            n_acf_lags=len(ACF_LAGS),
            n_bao=len(obs_bao_residuals),
        )

        # 2g — Primary FWER: within-diagnostic Bonferroni (§6.1)
        bonferroni = within_diagnostic_bonferroni(p_values)

        # 2h — Secondary FDR (§6.3)
        bh = benjamini_hochberg_within_diagnostic(p_values)

        # 2i — Family firing report
        for fam, r in bonferroni.items():
            mark = "FIRES" if r["fires"] else "no"
            print(
                f"  {fam:>7s}: {r['n_significant']:>3d}/{r['n_tests']:<3d} "
                f"significant at p ≤ {r['threshold']:.2e}  [{mark}]"
            )

        baseline_results[name] = {
            "obs_fit": obs_fit,
            "obs_MB": obs_MB,
            "obs_diagnostics": obs_diagnostics,
            "mock_summary": mock_summary,
            "p_values": p_values,
            "bonferroni": bonferroni,
            "bh": bh,
        }
        print(f"  Baseline {name} completed in {time.time() - t_start:.1f}s.")

    # === Step 3: Cross-diagnostic verdict per baseline (§6.2) ===
    print("\n=== Cross-diagnostic verdict per baseline ===")
    for name, results in baseline_results.items():
        positive, firing = cross_diagnostic_verdict(results["bonferroni"])
        results["positive_verdict"] = positive
        results["firing_families"] = set(firing)
        print(
            f"  {name}: {'POSITIVE' if positive else 'NULL'} "
            f"(firing: {sorted(firing) if firing else 'none'})"
        )

    # === Step 4: Combined positive-verdict criterion (§7.7) ===
    print("\n=== Combined positive-verdict criterion (§7.7) ===")
    lcdm = baseline_results["LambdaCDM"]
    wcdm = baseline_results["wCDM"]
    w0wa = baseline_results["w0waCDM"]

    lcdm_positive = lcdm["positive_verdict"]
    lcdm_families = lcdm["firing_families"]
    wcdm_preserves = lcdm_families.issubset(wcdm["firing_families"])
    w0wa_preserves = lcdm_families.issubset(w0wa["firing_families"])
    ersaf_positive = lcdm_positive and wcdm_preserves and w0wa_preserves

    print(f"  ΛCDM verdict (≥2 of 4 firing): {'POSITIVE' if lcdm_positive else 'NULL'}")
    print(f"  ΛCDM firing families: {sorted(lcdm_families) if lcdm_families else 'none'}")
    print(f"  wCDM preserves ΛCDM-firing families: {wcdm_preserves} "
          f"(wCDM firing: {sorted(wcdm['firing_families']) if wcdm['firing_families'] else 'none'})")
    print(f"  w₀wₐ CDM preserves ΛCDM-firing families: {w0wa_preserves} "
          f"(w₀wₐ firing: {sorted(w0wa['firing_families']) if w0wa['firing_families'] else 'none'})")
    print()
    print(f"  ERSAF VERDICT: {'POSITIVE' if ersaf_positive else 'NULL'}")

    # === Step 5: Persist outputs ===
    print("\n=== Writing outputs ===")
    summary = {
        "ersaf_verdict": "POSITIVE" if ersaf_positive else "NULL",
        "lcdm_verdict": "POSITIVE" if lcdm_positive else "NULL",
        "wcdm_preserves_lcdm_firing": bool(wcdm_preserves),
        "w0wa_preserves_lcdm_firing": bool(w0wa_preserves),
        "n_sn_post_cut": int(n_sn),
        "n_bao": int(len(bao_df)),
        "n_mocks": int(N_MOCKS),
        "master_seed": int(MASTER_SEED),
        "joint_cov_min_eigenvalue": float(min_eig),
        "baselines": {
            name: _serialize_baseline_for_json(r)
            for name, r in baseline_results.items()
        },
    }
    summary_path = out_dir / "ersaf_results.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Wrote summary: {summary_path}")

    for name, r in baseline_results.items():
        _save_baseline_arrays(out_dir, name, r)
        print(f"  Wrote arrays: {out_dir / f'ersaf_{name}_arrays.npz'}")

    print("\nERSAF run mode complete.")


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="ERSAF cosmology residual structure analysis."
    )
    parser.add_argument("--output-dir", default=".", help="Output directory")

    # Shared data-path arguments for both setup and run modes. Defaults match
    # the audit-specific layout `analysis/ersaf/data/` used by the dynametrix
    # repository's per-audit convention; the exact paths are pinned alongside
    # the SHA-256 hashes at lock-commit time (§11).
    data_paths = argparse.ArgumentParser(add_help=False)
    data_paths.add_argument(
        "--pantheon-data",
        default="analysis/ersaf/data/pantheon_plus/Pantheon+SH0ES.dat",
        help="Pantheon+ sample data file (default: %(default)s)",
    )
    data_paths.add_argument(
        "--pantheon-cov",
        default="analysis/ersaf/data/pantheon_plus/Pantheon+SH0ES_STAT+SYS.cov",
        help="Pantheon+ STAT+SYS covariance file (default: %(default)s)",
    )
    data_paths.add_argument(
        "--desi-path",
        default="analysis/ersaf/data/desi_dr1/",
        help="DESI DR1 BAO data directory containing desi_dr1_bao.csv and "
             "desi_dr1_bao_cov.npy (default: %(default)s)",
    )

    sub = parser.add_subparsers(dest="mode")
    sub.add_parser("setup", parents=[data_paths],
                   help="Materialize data, fit baselines, compute hashes")
    sub.add_parser("run", parents=[data_paths],
                   help="Execute full analysis pipeline")

    args = parser.parse_args()

    if args.mode == "setup":
        cmd_setup(args)
    elif args.mode == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()