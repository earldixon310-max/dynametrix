"""
ct_v1_novelty_diagnostic.py

EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED AS A CONFIRMATORY STUDY.

Tests whether CT-v1 (per CT_v1_FORMULA_LOCK.md) produces meaningfully different
values than the predecessor CT formula (v2/v3 unchanged, per
backend/app/services/feature_builder_v3.py) on the same atmospheric observation
data.

Per CT_v1_NOVELTY_REPRESENTATION_DIAGNOSTIC_PROTOCOL.md:
    D1 = Pearson correlation between CT-v1 and predecessor CT (GATE)
    D2-D5 = characterization diagnostics (informative for disclosure)

Cannot be cited as confirmatory evidence in any subsequent published audit.

Usage:
    python analysis/ct_v1_novelty/ct_v1_novelty_diagnostic.py \\
        --output analysis/ct_v1_novelty/DIAGNOSTIC_CT_v1_NOVELTY_2026-05-25.md

INTERPRETIVE CHOICES MADE AT IMPLEMENTATION TIME (locked in this script,
documented for transparency in the diagnostic output):

    1. "wind" in the formula lock's change/std terms (Sections 5.1, 5.5, 5.6):
       interpreted as wind_speed_10m. This is the surface wind measurement.
    2. "humidity" in the formula lock's change/std terms: interpreted as
       relative_humidity_2m.
    3. "wind_speed" in the storm intensity score (Section 5.2): interpreted
       as wind_speed_10m (same convention).
    4. "cloud_cover" proxy (Section 5.2): per the formula lock's
       pre-committed substitution, computed as
       1 - normalized(dewpoint_depression).
    5. Least-tuned region (Section 10 of protocol): selected as the location
       whose data entered the system most recently (highest min observed_at).
       Operationalized via simple recency rather than git-history parsing.

These choices were made in the script before any CT-v1 computation; they
resolve ambiguities in the formula lock without modifying it.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# -------------------------------------------------------------------------
# Backend integration
# -------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_PATH = _REPO_ROOT / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))

# Backend imports deferred to inside data-loading functions for testability.


# =========================================================================
# Locked configuration constants (per protocol; do not modify post-commit)
# =========================================================================

# Training-split boundary (protocol Section 5)
SPLIT_DATE = datetime(2026, 5, 15, 0, 0, 0, tzinfo=timezone.utc)

# Phase classifier parameters (formula lock Section 3)
KOISTINEN_A = 1.16      # Section 3.2
KOISTINEN_B = 0.66      # Section 3.2
ICE_GAUSSIAN_MU = -1.0  # Section 3.3
ICE_GAUSSIAN_SIGMA = 1.0
ICE_AMPLITUDE = 0.3
PRECIP_THRESHOLD = 0.1  # Section 3.4
PRECIP_RANGE = 1.0      # 0.1 to 1.1 mm/h maps to alpha 0 to 1

# Missing-data rule (formula lock Section 7)
MIN_COMPLETENESS_FRACTION = 0.75
ROLLING_WINDOW_3H = 3
ROLLING_WINDOW_6H = 6

# Bootstrap (protocol Section 6.3)
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = 0x1DEA

# Decision rule thresholds (protocol Section 6.4)
D1_PROCEED_THRESHOLD = 0.50
D1_ARCHIVE_THRESHOLD = 0.85

# Master formula epsilon (formula lock Section 1)
EPSILON = 1e-6

# Numerical guards
LOG_EPSILON = 1e-6


# =========================================================================
# Phase classifier (formula lock Section 3)
# =========================================================================

def wet_bulb_temperature(T: pd.Series, Td: pd.Series) -> pd.Series:
    """Stull simple approximation: T_w = T - (T - Td)/3 (Section 3.1)."""
    return T - (T - Td) / 3.0


def phase_probabilities(T_w: pd.Series, precipitation: pd.Series) -> pd.DataFrame:
    """Compute (p_rain, p_snow, p_ice, p_none) per formula lock Section 3.

    Returns a DataFrame with columns p_rain, p_snow, p_ice, p_none summing to 1.
    """
    # Section 3.2: Koistinen-Saltikoff snow probability
    p_snow_raw = 1.0 / (1.0 + np.exp((T_w - KOISTINEN_A) / KOISTINEN_B))

    # Section 3.3: Narrow Gaussian ice probability
    p_ice_raw = np.exp(
        -((T_w - ICE_GAUSSIAN_MU) ** 2) / (2.0 * ICE_GAUSSIAN_SIGMA ** 2)
    ) * ICE_AMPLITUDE

    # Section 3.4: Precipitation activity factor
    alpha = ((precipitation - PRECIP_THRESHOLD) / PRECIP_RANGE).clip(0.0, 1.0)

    # Section 3.5: Final normalized phase probabilities
    p_none = 1.0 - alpha
    p_snow = alpha * (1.0 - p_ice_raw) * p_snow_raw
    p_rain = alpha * (1.0 - p_ice_raw) * (1.0 - p_snow_raw)
    p_ice = alpha * p_ice_raw

    return pd.DataFrame({
        "p_rain": p_rain,
        "p_snow": p_snow,
        "p_ice": p_ice,
        "p_none": p_none,
    })


# =========================================================================
# Raw feature computation (per-location, rolling windows)
# =========================================================================

def compute_raw_features_per_location(df_loc: pd.DataFrame) -> pd.DataFrame:
    """For a single location's hourly atmospheric observations, compute raw
    (unnormalized) inputs for CT-v1 subcomponents.

    Input df_loc is expected to be sorted by observed_at ascending.
    Returns df_loc augmented with feature columns.
    """
    out = df_loc.copy()

    # Convert to consistent units & handle NaN-safe access
    temp = pd.to_numeric(out.get("temperature_2m"), errors="coerce")
    dewp = pd.to_numeric(out.get("dewpoint_2m"), errors="coerce")
    pres = pd.to_numeric(out.get("pressure_msl"), errors="coerce")
    wind = pd.to_numeric(out.get("wind_speed_10m"), errors="coerce")
    rh = pd.to_numeric(out.get("relative_humidity_2m"), errors="coerce")
    precip = pd.to_numeric(out.get("precipitation"), errors="coerce").fillna(0.0)
    cape = pd.to_numeric(out.get("cape"), errors="coerce").fillna(0.0)

    # --- 3-hour absolute changes (formula lock Section 5.1, 5.5) ---
    out["temp_change_3h_abs"] = temp.diff(ROLLING_WINDOW_3H).abs()
    out["pressure_change_3h_abs"] = pres.diff(ROLLING_WINDOW_3H).abs()
    out["wind_change_3h_abs"] = wind.diff(ROLLING_WINDOW_3H).abs()
    out["humidity_change_3h_abs"] = rh.diff(ROLLING_WINDOW_3H).abs()

    # --- 6-hour standard deviations (formula lock Section 5.6) ---
    out["temp_std_6h"] = temp.rolling(ROLLING_WINDOW_6H, min_periods=4).std()
    out["pressure_std_6h"] = pres.rolling(ROLLING_WINDOW_6H, min_periods=4).std()
    out["wind_std_6h"] = wind.rolling(ROLLING_WINDOW_6H, min_periods=4).std()
    out["humidity_std_6h"] = rh.rolling(ROLLING_WINDOW_6H, min_periods=4).std()

    # --- Phase probabilities (Section 3) ---
    T_w = wet_bulb_temperature(temp, dewp)
    out["wet_bulb_temp"] = T_w
    phase = phase_probabilities(T_w, precip)
    for col in phase.columns:
        out[col] = phase[col]

    # Dominant phase confidence and its 3-hour change (Section 5.1)
    out["dominant_phase_prob"] = phase[["p_rain", "p_snow", "p_ice", "p_none"]].max(axis=1)
    out["phase_change_3h"] = out["dominant_phase_prob"].diff(ROLLING_WINDOW_3H).abs()

    # --- Storm intensity raw inputs (Section 5.2) ---
    out["precipitation_rate"] = precip
    out["wind_speed_10m_raw"] = wind
    out["pressure_drop_6h"] = -pres.diff(ROLLING_WINDOW_6H)
    out["humidity_raw"] = rh
    out["dewpoint_depression"] = (temp - dewp)

    # --- Data quality proxy raw input (Section 5.7) ---
    # Count non-null observations in trailing 6-hour window (including current)
    # For "missing_fraction_6h" we need 6 expected observations
    out["non_null_count_6h"] = (
        pd.notna(temp).astype(int).rolling(ROLLING_WINDOW_6H, min_periods=1).sum()
    )
    out["missing_fraction_6h"] = 1.0 - (out["non_null_count_6h"] / ROLLING_WINDOW_6H)

    return out


def compute_raw_features_all_locations(df_all: pd.DataFrame) -> pd.DataFrame:
    """Apply per-location feature computation across all locations."""
    df_all = df_all.sort_values(["location_id", "observed_at"]).reset_index(drop=True)
    parts = []
    for loc_id, group in df_all.groupby("location_id"):
        group_sorted = group.sort_values("observed_at").reset_index(drop=True)
        enriched = compute_raw_features_per_location(group_sorted)
        parts.append(enriched)
    return pd.concat(parts, ignore_index=True)


# =========================================================================
# Normalization (formula lock Section 4)
# =========================================================================

NORMALIZATION_COLUMNS = [
    "temp_change_3h_abs",
    "pressure_change_3h_abs",
    "wind_change_3h_abs",
    "humidity_change_3h_abs",
    "phase_change_3h",
    "temp_std_6h",
    "pressure_std_6h",
    "wind_std_6h",
    "humidity_std_6h",
    "precipitation_rate",
    "wind_speed_10m_raw",
    "pressure_drop_6h",
    "humidity_raw",
    "dewpoint_depression",
]


@dataclass
class ScalingParameters:
    minmax: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    zscore: Dict[str, Tuple[float, float]] = field(default_factory=dict)   # (mean, std)
    quantile: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # (q05, q95)


def learn_scaling_parameters(df_train: pd.DataFrame) -> ScalingParameters:
    """Learn min/max, mean/std, and 5th/95th percentiles per feature from training subset."""
    scaling = ScalingParameters()
    for col in NORMALIZATION_COLUMNS:
        if col not in df_train.columns:
            continue
        s = df_train[col].dropna()
        if len(s) == 0:
            scaling.minmax[col] = (0.0, 1.0)
            scaling.zscore[col] = (0.0, 1.0)
            scaling.quantile[col] = (0.0, 1.0)
            continue
        scaling.minmax[col] = (float(s.min()), float(s.max()))
        std = float(s.std()) if len(s) > 1 else 1.0
        scaling.zscore[col] = (float(s.mean()), std if std > 0 else 1.0)
        scaling.quantile[col] = (float(s.quantile(0.05)), float(s.quantile(0.95)))
    return scaling


def apply_scaling(
    df: pd.DataFrame, scaling: ScalingParameters, scheme: str = "minmax"
) -> pd.DataFrame:
    """Apply locked scaling parameters to df. Returns new DataFrame with
    normalized versions of NORMALIZATION_COLUMNS (overwrites the originals).
    """
    out = df.copy()
    for col in NORMALIZATION_COLUMNS:
        if col not in out.columns:
            continue
        if scheme == "minmax":
            lo, hi = scaling.minmax.get(col, (0.0, 1.0))
            denom = (hi - lo) if (hi - lo) > 0 else 1.0
            out[col] = ((out[col] - lo) / denom).clip(0.0, 1.0)
        elif scheme == "zscore":
            mean, std = scaling.zscore.get(col, (0.0, 1.0))
            denom = std if std > 0 else 1.0
            # cap at ±3 sigma then rescale to [0,1]
            z = (out[col] - mean) / denom
            z = z.clip(-3.0, 3.0)
            out[col] = ((z + 3.0) / 6.0).clip(0.0, 1.0)
        elif scheme == "quantile":
            lo, hi = scaling.quantile.get(col, (0.0, 1.0))
            denom = (hi - lo) if (hi - lo) > 0 else 1.0
            out[col] = ((out[col] - lo) / denom).clip(0.0, 1.0)
        else:
            raise ValueError(f"Unknown scaling scheme: {scheme}")
    return out


# =========================================================================
# CT-v1 computation (formula lock Sections 5, 8)
# =========================================================================

def compute_ct_v1_subcomponents(df_n: pd.DataFrame) -> pd.DataFrame:
    """Given a DataFrame with normalized raw feature columns, compute the
    seven CT-v1 subcomponents (T, S, E, M, A, R, Q) and the master CT-v1.
    """
    out = df_n.copy()

    # --- T: storm transition score (Section 5.1) ---
    # mean(|dT|, |dP|, |dW|, |dH|, phase_change_3h)
    t_inputs = out[[
        "temp_change_3h_abs",
        "pressure_change_3h_abs",
        "wind_change_3h_abs",
        "humidity_change_3h_abs",
        "phase_change_3h",
    ]]
    out["T"] = t_inputs.mean(axis=1, skipna=True)

    # --- S: storm intensity score (Section 5.2) ---
    # mean(precip, wind, pressure_drop_6h, humidity, cloud_cover)
    # cloud_cover proxy = 1 - dewpoint_depression_normalized (per formula lock)
    cloud_cover_proxy = 1.0 - out["dewpoint_depression"]
    s_inputs = pd.DataFrame({
        "precipitation_rate": out["precipitation_rate"],
        "wind_speed_10m_raw": out["wind_speed_10m_raw"],
        "pressure_drop_6h": out["pressure_drop_6h"],
        "humidity_raw": out["humidity_raw"],
        "cloud_cover_proxy": cloud_cover_proxy.clip(0.0, 1.0),
    })
    out["S"] = s_inputs.mean(axis=1, skipna=True)

    # --- E: phase probability entropy (Section 5.3) ---
    # -sum(p_i * log(p_i + eps)) / log(4)
    p_cols = ["p_rain", "p_snow", "p_ice", "p_none"]
    p_arr = out[p_cols].values
    log_p = np.log(p_arr + LOG_EPSILON)
    out["E"] = (-(p_arr * log_p).sum(axis=1)) / np.log(4.0)
    out["E"] = out["E"].clip(0.0, 1.0)

    # --- M: phase mix score (Section 5.4) ---
    out["M"] = 1.0 - out[p_cols].max(axis=1)

    # --- A: atmospheric stability proxy (Section 5.5) ---
    a_inputs = out[[
        "temp_change_3h_abs",
        "pressure_change_3h_abs",
        "wind_change_3h_abs",
        "humidity_change_3h_abs",
    ]]
    out["A"] = 1.0 - a_inputs.mean(axis=1, skipna=True)
    out["A"] = out["A"].clip(0.0, 1.0)

    # --- R: reliability proxy (Section 5.6) ---
    r_inputs = out[[
        "temp_std_6h",
        "pressure_std_6h",
        "wind_std_6h",
        "humidity_std_6h",
    ]]
    out["R"] = 1.0 - r_inputs.mean(axis=1, skipna=True)
    out["R"] = out["R"].clip(0.0, 1.0)

    # --- Q: data quality proxy (Section 5.7) ---
    out["Q"] = 1.0 - out["missing_fraction_6h"]
    out["Q"] = out["Q"].clip(0.0, 1.0)

    return out


def compute_ct_v1(
    df_n: pd.DataFrame,
    e_override: Optional[float] = None,
    m_override: Optional[float] = None,
    uniform_weights: bool = False,
) -> pd.Series:
    """Compute master CT-v1 value per row.

    e_override / m_override: if provided, replace the corresponding term with
    a constant (used by D3 ablation diagnostic).

    uniform_weights: if True, use 0.5/0.5, 0.5/0.5, 0.33/0.33/0.33 weighting
    (used by D3 uniform-weights ablation).
    """
    df_sub = compute_ct_v1_subcomponents(df_n)

    T = df_sub["T"]
    S = df_sub["S"]
    E = df_sub["E"] if e_override is None else pd.Series(e_override, index=df_sub.index)
    M = df_sub["M"] if m_override is None else pd.Series(m_override, index=df_sub.index)
    A = df_sub["A"]
    R = df_sub["R"]
    Q = df_sub["Q"]

    if uniform_weights:
        I = 0.5 * T + 0.5 * S
        C = 0.5 * E + 0.5 * M
        P = (T * 0 + 1) * (1.0 / 3.0 * A + 1.0 / 3.0 * R + 1.0 / 3.0 * Q)
    else:
        I = 0.6 * T + 0.4 * S
        C = 0.7 * E + 0.3 * M
        P = 0.5 * A + 0.3 * R + 0.2 * Q

    ct = (I * C) / np.sqrt(P + EPSILON)
    return ct


# =========================================================================
# Predecessor CT computation (via existing feature_builder_v3)
# =========================================================================

def compute_predecessor_ct(df_atm: pd.DataFrame) -> pd.Series:
    """Compute predecessor CT (v2/v3 unchanged formula) by calling the
    existing feature_builder_v3.build_enriched_features_v3 per location.

    Returns a Series aligned with df_atm's index containing the CT column.
    """
    from app.services.feature_builder_v3 import build_enriched_features_v3

    df_sorted = df_atm.sort_values(["location_id", "observed_at"]).reset_index(drop=True)
    parts = []
    for loc_id, group in df_sorted.groupby("location_id"):
        g = group.sort_values("observed_at").reset_index(drop=True)
        # Ensure the columns build_enriched_features_v3 expects are present
        enriched = build_enriched_features_v3(g)
        parts.append(enriched[["location_id", "observed_at", "CT"]])
    df_ct = pd.concat(parts, ignore_index=True)
    # Reindex to match df_atm
    df_ct_indexed = df_ct.set_index(["location_id", "observed_at"])
    df_atm_indexed = df_atm.set_index(["location_id", "observed_at"])
    aligned = df_ct_indexed.reindex(df_atm_indexed.index)["CT"]
    return aligned.reset_index(drop=True)


# =========================================================================
# Data loading
# =========================================================================

def load_atmospheric_observations() -> pd.DataFrame:
    """Load all atmospheric_observations rows into a DataFrame."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.db.models.engine import AtmosphericObservation

    cols = [
        "id", "location_id", "source", "observed_at",
        "cape", "temperature_2m", "dewpoint_2m", "relative_humidity_2m",
        "pressure_msl",
        "wind_speed_10m", "wind_speed_80m", "wind_speed_180m",
        "precipitation",
    ]
    stmt = select(*[getattr(AtmosphericObservation, c) for c in cols]).order_by(
        AtmosphericObservation.location_id, AtmosphericObservation.observed_at
    )
    with SessionLocal() as db:
        rows = db.execute(stmt).all()
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols)
    # Ensure observed_at is timezone-aware UTC
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
    df["location_id"] = df["location_id"].astype(str)
    return df


# =========================================================================
# Filtering: apply 75% completeness rule (formula lock Section 7)
# =========================================================================

def apply_completeness_filter(df_features: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where missing_fraction_6h exceeds the 25% threshold (i.e.,
    fewer than 75% of expected observations are present).
    """
    mask = df_features["missing_fraction_6h"] <= (1.0 - MIN_COMPLETENESS_FRACTION)
    return df_features[mask].copy()


# =========================================================================
# D1 — Structural similarity (GATE)
# =========================================================================

def pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation with NaN-safe handling."""
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 2:
        return float("nan")
    xc = x[mask] - x[mask].mean()
    yc = y[mask] - y[mask].mean()
    num = float((xc * yc).sum())
    den = float(np.sqrt((xc ** 2).sum() * (yc ** 2).sum()))
    return num / den if den > 0 else 0.0


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation."""
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 2:
        return float("nan")
    xr = pd.Series(x[mask]).rank().values
    yr = pd.Series(y[mask]).rank().values
    return pearson(xr, yr)


@dataclass
class D1Result:
    point_estimate: float
    ci_lo: float
    ci_hi: float
    spearman_secondary: float
    n_paired: int


def compute_d1(
    ct_pred: pd.Series, ct_v1: pd.Series
) -> D1Result:
    """D1: Pearson correlation between predecessor CT and CT-v1, with
    percentile bootstrap CI.
    """
    x = ct_pred.values.astype(float)
    y = ct_v1.values.astype(float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x = x[mask]
    y = y[mask]

    point = pearson(x, y)
    spearman_val = spearman(x, y)

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(x)
    if n < 2:
        return D1Result(point, float("nan"), float("nan"), spearman_val, n)

    boot = np.empty(BOOTSTRAP_B)
    for b in range(BOOTSTRAP_B):
        idx = rng.integers(0, n, size=n)
        boot[b] = pearson(x[idx], y[idx])

    ci_lo = float(np.percentile(boot, 2.5))
    ci_hi = float(np.percentile(boot, 97.5))
    return D1Result(point, ci_lo, ci_hi, spearman_val, n)


def decision_from_d1(r: float) -> Tuple[str, str]:
    """Apply protocol Section 6.4 decision rule."""
    if r < D1_PROCEED_THRESHOLD:
        return ("PROCEED",
                f"Pearson correlation {r:.4f} < {D1_PROCEED_THRESHOLD} threshold. "
                "CT-v1's structural content is doing work distinct from predecessor formula. "
                "Advance to full AEPF cross-model review and lock as confirmatory study.")
    if r <= D1_ARCHIVE_THRESHOLD:
        return ("PROCEED_WITH_DISCLOSURE",
                f"Pearson correlation {r:.4f} is in "
                f"[{D1_PROCEED_THRESHOLD}, {D1_ARCHIVE_THRESHOLD}]. "
                "Partial correlation with previously-falsified predecessor. "
                "Advance to lock, but pre-registration must explicitly disclose "
                "the bounded informational content in §9.")
    return ("ARCHIVE",
            f"Pearson correlation {r:.4f} > {D1_ARCHIVE_THRESHOLD} threshold. "
            "CT-v1 tracks predecessor formula too closely; the structural refinements "
            "are not producing meaningfully different outputs. Archive as "
            "considered-but-deferred alongside Dynametrix-HRRR pre-registration.")


# =========================================================================
# D2 — Representation-equivalence stress test
# =========================================================================

def perturbation_p1_zscore(
    df_raw_comp: pd.DataFrame, scaling: ScalingParameters
) -> Tuple[pd.Series, pd.Series]:
    """P1: re-compute CT-v1 and predecessor CT with z-score normalization."""
    df_n = apply_scaling(df_raw_comp, scaling, scheme="zscore")
    ct_v1 = compute_ct_v1(df_n)
    # Predecessor uses its own internal normalization; z-score doesn't apply.
    # For P1, we compute CT-v1 under z-score and compare its delta vs baseline
    # CT-v1; predecessor delta is taken as 0 (predecessor is not affected by
    # CT-v1's normalization choice).
    ct_pred = pd.Series(np.zeros(len(df_raw_comp)), index=df_raw_comp.index)
    return ct_v1, ct_pred


def perturbation_p2_phase_shift(
    df_raw_comp: pd.DataFrame, scaling: ScalingParameters
) -> Tuple[pd.Series, pd.Series]:
    """P2: shift each phase probability by +0.02 then renormalize.
    Predecessor doesn't use explicit phase probabilities, so this perturbation
    is CT-v1-only.
    """
    df_perturbed = df_raw_comp.copy()
    for col in ["p_rain", "p_snow", "p_ice", "p_none"]:
        df_perturbed[col] = df_perturbed[col] + 0.02
    # Renormalize
    p_sum = df_perturbed[["p_rain", "p_snow", "p_ice", "p_none"]].sum(axis=1)
    for col in ["p_rain", "p_snow", "p_ice", "p_none"]:
        df_perturbed[col] = df_perturbed[col] / p_sum
    # Recompute dominant_phase_prob and phase_change_3h since they depend on phase probs
    df_perturbed["dominant_phase_prob"] = df_perturbed[
        ["p_rain", "p_snow", "p_ice", "p_none"]
    ].max(axis=1)
    df_perturbed["phase_change_3h"] = df_perturbed.groupby("location_id")[
        "dominant_phase_prob"
    ].diff(ROLLING_WINDOW_3H).abs()

    df_n = apply_scaling(df_perturbed, scaling, scheme="minmax")
    ct_v1 = compute_ct_v1(df_n)
    ct_pred = pd.Series([np.nan] * len(df_raw_comp), index=df_raw_comp.index)
    return ct_v1, ct_pred


def perturbation_p3_4h_temp(
    df_raw: pd.DataFrame, scaling: ScalingParameters
) -> Tuple[pd.Series, pd.Series]:
    """P3: replace 3h temperature change with 4h temperature change.
    Affects T and A.
    """
    df_perturbed = df_raw.copy()
    # Recompute temp_change with 4h window per location
    def _recompute(g):
        g = g.sort_values("observed_at").reset_index(drop=True)
        temp = pd.to_numeric(g["temperature_2m"], errors="coerce")
        g["temp_change_3h_abs"] = temp.diff(4).abs()
        return g
    df_perturbed = df_perturbed.groupby("location_id", group_keys=False).apply(_recompute)

    df_n = apply_scaling(df_perturbed, scaling, scheme="minmax")
    ct_v1 = compute_ct_v1(df_n)
    ct_pred = pd.Series([np.nan] * len(df_perturbed), index=df_perturbed.index)
    return ct_v1, ct_pred


def perturbation_p4_interpolate(
    df_raw_comp: pd.DataFrame, scaling: ScalingParameters
) -> Tuple[pd.Series, pd.Series]:
    """P4: replace missing-data drop with linear interpolation.
    Affects Q and rolling-window computations.
    """
    df_perturbed = df_raw_comp.copy()
    # Linearly interpolate temperature, dewpoint, pressure, wind, humidity
    for col in ["temperature_2m", "dewpoint_2m", "pressure_msl",
                "wind_speed_10m", "relative_humidity_2m"]:
        if col in df_perturbed.columns:
            df_perturbed[col] = df_perturbed.groupby("location_id")[col].transform(
                lambda x: pd.to_numeric(x, errors="coerce").interpolate()
            )
    # Recompute features
    df_perturbed = compute_raw_features_all_locations(df_perturbed)
    df_n = apply_scaling(df_perturbed, scaling, scheme="minmax")
    ct_v1 = compute_ct_v1(df_n)
    ct_pred = pd.Series([np.nan] * len(df_perturbed), index=df_perturbed.index)
    return ct_v1, ct_pred


def perturbation_p5_phase_encoding(
    df_raw_comp: pd.DataFrame, scaling: ScalingParameters
) -> Tuple[pd.Series, pd.Series]:
    """P5: recompute p_rain as 1 - p_snow - p_ice - p_none (alternate equivalent encoding)."""
    df_perturbed = df_raw_comp.copy()
    df_perturbed["p_rain"] = (
        1.0 - df_perturbed["p_snow"] - df_perturbed["p_ice"] - df_perturbed["p_none"]
    ).clip(0.0, 1.0)
    # Renormalize to ensure sum = 1
    p_sum = df_perturbed[["p_rain", "p_snow", "p_ice", "p_none"]].sum(axis=1)
    for col in ["p_rain", "p_snow", "p_ice", "p_none"]:
        df_perturbed[col] = df_perturbed[col] / p_sum

    df_n = apply_scaling(df_perturbed, scaling, scheme="minmax")
    ct_v1 = compute_ct_v1(df_n)
    ct_pred = pd.Series([np.nan] * len(df_perturbed), index=df_perturbed.index)
    return ct_v1, ct_pred


@dataclass
class D2Result:
    delta_v1: Dict[str, float]   # per-perturbation median |Δ CT-v1|
    delta_pred: Dict[str, float]  # per-perturbation median |Δ CT-pred| (NaN if undefined)
    rank_correlation: float       # Spearman rank correlation over P1,P3,P4,P5


def compute_d2(
    df_raw_comp: pd.DataFrame,
    ct_v1_baseline: pd.Series,
    ct_pred_baseline: pd.Series,
    scaling: ScalingParameters,
) -> D2Result:
    """D2: Representation-equivalence stress test."""
    perturbations = {
        "P1_zscore": perturbation_p1_zscore,
        "P2_phase_shift": perturbation_p2_phase_shift,
        "P3_4h_temp": perturbation_p3_4h_temp,
        "P4_interpolate": perturbation_p4_interpolate,
        "P5_phase_encoding": perturbation_p5_phase_encoding,
    }

    delta_v1 = {}
    delta_pred = {}

    for p_id, p_fn in perturbations.items():
        try:
            ct_v1_pert, ct_pred_pert = p_fn(df_raw_comp, scaling)
            # Align by index
            v1_diff = (ct_v1_pert.values - ct_v1_baseline.values)
            v1_diff = v1_diff[~np.isnan(v1_diff)]
            delta_v1[p_id] = float(np.median(np.abs(v1_diff))) if len(v1_diff) > 0 else float("nan")
            # For perturbations where predecessor is unaffected, delta_pred = NaN
            if p_id in ("P1_zscore",):
                # P1 affects CT-v1's normalization but not predecessor's internal scaling
                delta_pred[p_id] = 0.0
            elif p_id in ("P2_phase_shift", "P5_phase_encoding"):
                # Predecessor doesn't use explicit phase probabilities
                delta_pred[p_id] = float("nan")
            else:
                # P3, P4 affect both — recompute predecessor under perturbation
                # P3 needs predecessor recompute with 4h temp change.
                # P4 needs predecessor recompute with interpolated inputs.
                # For simplicity, compute predecessor delta only where the
                # predecessor pipeline can absorb the perturbation; otherwise NaN.
                # Predecessor uses its own internal scaling and rolling windows.
                # For P3 (4h temp), predecessor doesn't use temp change in its formula
                # so delta_pred = 0.
                # For P4 (interpolation), predecessor will see interpolated atmospheric
                # inputs, which will propagate through its features.
                if p_id == "P3_4h_temp":
                    delta_pred[p_id] = 0.0  # predecessor doesn't depend on temp change directly
                elif p_id == "P4_interpolate":
                    # Recompute predecessor with interpolated data
                    df_p = df_raw_comp.copy()
                    for col in ["temperature_2m", "dewpoint_2m", "pressure_msl",
                                "wind_speed_10m", "relative_humidity_2m"]:
                        if col in df_p.columns:
                            df_p[col] = df_p.groupby("location_id")[col].transform(
                                lambda x: pd.to_numeric(x, errors="coerce").interpolate()
                            )
                    ct_pred_p4 = compute_predecessor_ct(df_p)
                    pred_diff = (ct_pred_p4.values - ct_pred_baseline.values)
                    pred_diff = pred_diff[~np.isnan(pred_diff)]
                    delta_pred[p_id] = float(np.median(np.abs(pred_diff))) if len(pred_diff) > 0 else float("nan")
                else:
                    delta_pred[p_id] = float("nan")
        except Exception as exc:
            print(f"      WARN: D2 perturbation {p_id} failed: {type(exc).__name__}: {exc}")
            delta_v1[p_id] = float("nan")
            delta_pred[p_id] = float("nan")

    # Rank correlation over perturbations where both deltas are defined
    paired = [
        (p_id, delta_v1[p_id], delta_pred[p_id])
        for p_id in delta_v1
        if not np.isnan(delta_v1[p_id]) and not np.isnan(delta_pred[p_id])
    ]
    if len(paired) >= 2:
        v1_arr = np.array([p[1] for p in paired])
        pred_arr = np.array([p[2] for p in paired])
        rank_corr = spearman(v1_arr, pred_arr)
    else:
        rank_corr = float("nan")

    return D2Result(delta_v1=delta_v1, delta_pred=delta_pred, rank_correlation=rank_corr)


# =========================================================================
# D3 — Entropy + mix ablation
# =========================================================================

@dataclass
class D3Result:
    r_no_e: float
    r_no_m: float
    r_uniform_weights: float
    train_median_e: float
    train_median_m: float


def compute_d3(
    df_n_train: pd.DataFrame,
    df_n_comp: pd.DataFrame,
    ct_v1_full: pd.Series,
) -> D3Result:
    """D3: Ablation diagnostic — replace E or M with training-set medians."""
    # Compute training-set medians of normalized E and M
    train_sub = compute_ct_v1_subcomponents(df_n_train)
    e_med = float(np.nanmedian(train_sub["E"]))
    m_med = float(np.nanmedian(train_sub["M"]))

    ct_no_e = compute_ct_v1(df_n_comp, e_override=e_med)
    ct_no_m = compute_ct_v1(df_n_comp, m_override=m_med)
    ct_uniform = compute_ct_v1(df_n_comp, uniform_weights=True)

    return D3Result(
        r_no_e=pearson(ct_no_e.values, ct_v1_full.values),
        r_no_m=pearson(ct_no_m.values, ct_v1_full.values),
        r_uniform_weights=pearson(ct_uniform.values, ct_v1_full.values),
        train_median_e=e_med,
        train_median_m=m_med,
    )


# =========================================================================
# D4 — Normalization control
# =========================================================================

@dataclass
class D4Result:
    r_minmax: float
    r_zscore: float
    r_quantile: float


def compute_d4(
    df_raw_comp: pd.DataFrame,
    ct_pred: pd.Series,
    scaling: ScalingParameters,
) -> D4Result:
    """D4: Recompute CT-v1 under three normalization schemes and check
    correlation with predecessor CT under each.
    """
    df_minmax = apply_scaling(df_raw_comp, scaling, scheme="minmax")
    df_zscore = apply_scaling(df_raw_comp, scaling, scheme="zscore")
    df_quantile = apply_scaling(df_raw_comp, scaling, scheme="quantile")

    ct_minmax = compute_ct_v1(df_minmax)
    ct_zscore = compute_ct_v1(df_zscore)
    ct_quantile = compute_ct_v1(df_quantile)

    return D4Result(
        r_minmax=pearson(ct_pred.values, ct_minmax.values),
        r_zscore=pearson(ct_pred.values, ct_zscore.values),
        r_quantile=pearson(ct_pred.values, ct_quantile.values),
    )


# =========================================================================
# D5 — Least-tuned region comparison
# =========================================================================

@dataclass
class D5Result:
    least_tuned_location_id: str
    r_all_locations: float
    r_least_tuned_only: float
    r_complement: float
    n_least_tuned: int
    n_complement: int


def select_least_tuned_location(df_features: pd.DataFrame) -> str:
    """Per protocol Section 10.2, simplified to: location whose data entered
    the system most recently (highest min observed_at).
    """
    by_loc = df_features.groupby("location_id")["observed_at"].min()
    return str(by_loc.idxmax())


def compute_d5(
    df_features_comp: pd.DataFrame,
    ct_pred_comp: pd.Series,
    ct_v1_comp: pd.Series,
    least_tuned_id: str,
) -> D5Result:
    """D5: structural similarity correlation in least-tuned vs other regions."""
    df = df_features_comp.copy()
    df["ct_pred"] = ct_pred_comp.values
    df["ct_v1"] = ct_v1_comp.values

    all_r = pearson(df["ct_pred"].values, df["ct_v1"].values)

    least_mask = df["location_id"] == least_tuned_id
    least_df = df[least_mask]
    comp_df = df[~least_mask]

    least_r = pearson(least_df["ct_pred"].values, least_df["ct_v1"].values) if len(least_df) > 1 else float("nan")
    comp_r = pearson(comp_df["ct_pred"].values, comp_df["ct_v1"].values) if len(comp_df) > 1 else float("nan")

    return D5Result(
        least_tuned_location_id=least_tuned_id,
        r_all_locations=all_r,
        r_least_tuned_only=least_r,
        r_complement=comp_r,
        n_least_tuned=int(least_mask.sum()),
        n_complement=int((~least_mask).sum()),
    )


# =========================================================================
# Output writer
# =========================================================================

def write_diagnostic_output(
    output_path: Path,
    n_train: int,
    n_comp: int,
    n_excluded: int,
    d1: D1Result,
    d1_verdict: str,
    d1_explanation: str,
    d2: Optional[D2Result],
    d3: Optional[D3Result],
    d4: Optional[D4Result],
    d5: Optional[D5Result],
) -> None:
    today = date.today().isoformat()
    lines = []
    lines.append("# Diagnostic: CT-v1 Novelty + Representation")
    lines.append("")
    lines.append("**Status:** EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED.")
    lines.append("")
    lines.append(f"**Date:** {today}")
    lines.append(f"**Operator:** Earl Dixon")
    lines.append(f"**Protocol:** `CT_v1_NOVELTY_REPRESENTATION_DIAGNOSTIC_PROTOCOL.md`")
    lines.append(f"**Formula lock:** `CT_v1_FORMULA_LOCK.md`")
    lines.append("")
    lines.append("## Data summary")
    lines.append(f"- Training subset (observed_at < 2026-05-15 UTC): {n_train:,} cells")
    lines.append(f"- Comparison subset (observed_at >= 2026-05-15 UTC): {n_comp:,} cells")
    lines.append(f"- Cells excluded by 75% completeness rule: {n_excluded:,}")
    lines.append(f"- D1 paired cells (both predecessor CT and CT-v1 defined): {d1.n_paired:,}")
    lines.append("")
    lines.append("## D1 — Structural similarity (GATE)")
    lines.append("")
    lines.append(f"**Pearson correlation (predecessor CT vs CT-v1):** {d1.point_estimate:.4f}")
    lines.append(f"**95% bootstrap CI:** [{d1.ci_lo:.4f}, {d1.ci_hi:.4f}]")
    lines.append(f"**Bootstrap:** B = {BOOTSTRAP_B:,}, seed = 0x{BOOTSTRAP_SEED:X}")
    lines.append(f"**Spearman (secondary, reported for transparency):** {d1.spearman_secondary:.4f}")
    lines.append("")
    lines.append("### Verdict")
    lines.append("")
    lines.append(f"**{d1_verdict}**")
    lines.append("")
    lines.append(d1_explanation)
    lines.append("")

    if d2 is not None:
        lines.append("## D2 — Representation-equivalence stress test (characterization)")
        lines.append("")
        lines.append("Per-perturbation median |Δ CT|:")
        lines.append("")
        lines.append("| Perturbation | Δ CT-v1 | Δ CT-pred |")
        lines.append("|---|---|---|")
        for p_id in ["P1_zscore", "P2_phase_shift", "P3_4h_temp", "P4_interpolate", "P5_phase_encoding"]:
            v1 = d2.delta_v1.get(p_id, float("nan"))
            pred = d2.delta_pred.get(p_id, float("nan"))
            v1_s = f"{v1:.4f}" if not np.isnan(v1) else "NaN"
            pred_s = f"{pred:.4f}" if not np.isnan(pred) else "N/A"
            lines.append(f"| {p_id} | {v1_s} | {pred_s} |")
        lines.append("")
        lines.append(f"**Rank correlation of perturbation sensitivities (Spearman):** "
                     f"{d2.rank_correlation:.4f}")
        lines.append("")

    if d3 is not None:
        lines.append("## D3 — Entropy + mix ablation (characterization)")
        lines.append("")
        lines.append(f"**Training-set median of normalized E:** {d3.train_median_e:.4f}")
        lines.append(f"**Training-set median of normalized M:** {d3.train_median_m:.4f}")
        lines.append("")
        lines.append("Correlation with full CT-v1 under each ablation variant:")
        lines.append("")
        lines.append("| Variant | Correlation with full CT-v1 |")
        lines.append("|---|---|")
        lines.append(f"| CT-v1 without E (E → training median) | {d3.r_no_e:.4f} |")
        lines.append(f"| CT-v1 without M (M → training median) | {d3.r_no_m:.4f} |")
        lines.append(f"| CT-v1 with uniform weights | {d3.r_uniform_weights:.4f} |")
        lines.append("")

    if d4 is not None:
        lines.append("## D4 — Normalization control (characterization)")
        lines.append("")
        lines.append("Correlation of CT-v1 with predecessor CT under each normalization scheme:")
        lines.append("")
        lines.append("| Scheme | Pearson(CT-v1, CT-pred) |")
        lines.append("|---|---|")
        lines.append(f"| Min-max (locked) | {d4.r_minmax:.4f} |")
        lines.append(f"| Z-score | {d4.r_zscore:.4f} |")
        lines.append(f"| Quantile (5th/95th) | {d4.r_quantile:.4f} |")
        lines.append("")

    if d5 is not None:
        lines.append("## D5 — Least-tuned region comparison (characterization)")
        lines.append("")
        lines.append(f"**Least-tuned location (highest min observed_at):** `{d5.least_tuned_location_id}`")
        lines.append(f"**All locations pooled:** r = {d5.r_all_locations:.4f} (n = {d5.n_least_tuned + d5.n_complement:,})")
        lines.append(f"**Least-tuned region only:** r = {d5.r_least_tuned_only:.4f} (n = {d5.n_least_tuned:,})")
        lines.append(f"**Complement (all other locations):** r = {d5.r_complement:.4f} (n = {d5.n_complement:,})")
        lines.append("")

    lines.append("## Interpretive choices made at implementation time")
    lines.append("")
    lines.append("- 'wind' in formula lock Sections 5.1, 5.5, 5.6 interpreted as wind_speed_10m.")
    lines.append("- 'humidity' interpreted as relative_humidity_2m.")
    lines.append("- 'cloud_cover' computed via dewpoint depression proxy (formula lock Section 5.2).")
    lines.append("- 'least-tuned region' selected by recency of first observation (protocol Section 10.2 tiebreaker).")
    lines.append("- May 4-7 data-collection gap (task #92) handled by 75% completeness rule; affected cells excluded.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. Cannot be cited as confirmatory")
    lines.append("evidence in any subsequent published audit. If the finding turns out to be")
    lines.append("substantively interesting in its own right, it must be re-derived under proper")
    lines.append("AEPF lock discipline before publication.*")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote diagnostic output to {output_path}")


# =========================================================================
# Main entrypoint
# =========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Path to write the diagnostic summary markdown")
    parser.add_argument("--sanity-only", action="store_true",
                        help="Run sanity check only: load tiny slice, compute CT-v1, no D1-D5 comparison")
    args = parser.parse_args()

    print("[1/7] Loading atmospheric_observations...")
    df_all = load_atmospheric_observations()
    print(f"      Loaded {len(df_all):,} atmospheric observations across "
          f"{df_all['location_id'].nunique()} locations.")

    if df_all.empty:
        print("ERROR: No atmospheric observations found.")
        return 1

    print("[2/7] Computing raw features (rolling windows per location)...")
    df_features = compute_raw_features_all_locations(df_all)
    print(f"      Computed features for {len(df_features):,} rows.")

    print("[3/7] Applying 75% completeness filter...")
    n_before = len(df_features)
    df_features = apply_completeness_filter(df_features)
    n_excluded = n_before - len(df_features)
    print(f"      Kept {len(df_features):,} cells; excluded {n_excluded:,} for completeness.")

    df_train = df_features[df_features["observed_at"] < SPLIT_DATE].copy()
    df_comp = df_features[df_features["observed_at"] >= SPLIT_DATE].copy()
    print(f"      Training subset (< {SPLIT_DATE.date()}): {len(df_train):,} cells")
    print(f"      Comparison subset (>= {SPLIT_DATE.date()}): {len(df_comp):,} cells")

    if args.sanity_only:
        print("\n=== SANITY CHECK MODE ===")
        # Pick a single location, first 24 hours, compute CT-v1
        first_loc = df_train["location_id"].iloc[0]
        sample = df_train[df_train["location_id"] == first_loc].head(48).copy()
        print(f"      Sanity sample: location={first_loc}, {len(sample)} rows")
        scaling = learn_scaling_parameters(df_train)
        sample_n = apply_scaling(sample, scaling, scheme="minmax")
        sample_ct = compute_ct_v1(sample_n)
        non_nan = sample_ct.dropna()
        if len(non_nan) == 0:
            print("ERROR: All CT-v1 values are NaN. Implementation problem.")
            return 1
        print(f"      CT-v1 stats over sample: "
              f"n={len(non_nan)}, min={non_nan.min():.4f}, "
              f"max={non_nan.max():.4f}, mean={non_nan.mean():.4f}")
        print(f"      Sanity check PASSED (CT-v1 computes non-degenerately).")
        return 0

    print("[4/7] Learning normalization parameters from training subset...")
    scaling = learn_scaling_parameters(df_train)

    print("[5/7] Computing CT-v1 and predecessor CT on comparison subset...")
    df_comp_n = apply_scaling(df_comp, scaling, scheme="minmax")
    ct_v1 = compute_ct_v1(df_comp_n)
    # For predecessor, we need to pass df_all-style records (raw atmospheric data)
    # to feature_builder_v3. The features it computes overlap with ours but use
    # different normalization. We pass the raw observations restricted to the
    # comparison time window.
    df_atm_comp = df_all[df_all["observed_at"] >= SPLIT_DATE].copy()
    ct_pred = compute_predecessor_ct(df_atm_comp)
    # Align ct_pred to df_comp's order
    df_atm_comp_keyed = df_atm_comp.set_index(["location_id", "observed_at"])
    ct_pred_series = pd.Series(ct_pred.values, index=df_atm_comp_keyed.index)
    df_comp_keyed = df_comp.set_index(["location_id", "observed_at"])
    ct_pred_aligned = ct_pred_series.reindex(df_comp_keyed.index).reset_index(drop=True)

    print(f"      CT-v1 non-NaN: {ct_v1.notna().sum():,}; predecessor CT non-NaN: {ct_pred_aligned.notna().sum():,}")

    print(f"[6/7] Computing D1 (gate) with bootstrap (B={BOOTSTRAP_B:,})...")
    d1 = compute_d1(ct_pred_aligned, ct_v1)
    verdict, explanation = decision_from_d1(d1.point_estimate)
    print(f"      r = {d1.point_estimate:.4f}, 95% CI = [{d1.ci_lo:.4f}, {d1.ci_hi:.4f}]")
    print(f"      VERDICT: {verdict}")

    d2 = d3 = d4 = d5 = None
    if verdict != "ARCHIVE":
        print("[7/7] Computing D2-D5 characterization diagnostics...")

        df_train_n = apply_scaling(df_train, scaling, scheme="minmax")

        print("      D2: representation-equivalence stress test...")
        d2 = compute_d2(df_comp, ct_v1, ct_pred_aligned, scaling)
        print(f"          Perturbation rank-correlation (Spearman): {d2.rank_correlation:.4f}")

        print("      D3: entropy + mix ablation...")
        d3 = compute_d3(df_train_n, df_comp_n, ct_v1)
        print(f"          r(no-E) = {d3.r_no_e:.4f}, r(no-M) = {d3.r_no_m:.4f}, "
              f"r(uniform) = {d3.r_uniform_weights:.4f}")

        print("      D4: normalization control...")
        d4 = compute_d4(df_comp, ct_pred_aligned, scaling)
        print(f"          r(minmax)={d4.r_minmax:.4f}, "
              f"r(zscore)={d4.r_zscore:.4f}, "
              f"r(quantile)={d4.r_quantile:.4f}")

        print("      D5: least-tuned region comparison...")
        least_tuned = select_least_tuned_location(df_features)
        d5 = compute_d5(df_comp, ct_pred_aligned, ct_v1, least_tuned)
        print(f"          least-tuned location: {least_tuned}")
        print(f"          r(all)={d5.r_all_locations:.4f}, "
              f"r(least)={d5.r_least_tuned_only:.4f} (n={d5.n_least_tuned}), "
              f"r(complement)={d5.r_complement:.4f} (n={d5.n_complement})")
    else:
        print("[7/7] D2-D5 skipped per protocol §11 (D1 returned ARCHIVE).")

    write_diagnostic_output(
        output_path=args.output,
        n_train=len(df_train),
        n_comp=len(df_comp),
        n_excluded=n_excluded,
        d1=d1,
        d1_verdict=verdict,
        d1_explanation=explanation,
        d2=d2, d3=d3, d4=d4, d5=d5,
    )

    print(f"\n=== DIAGNOSTIC VERDICT: {verdict} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
