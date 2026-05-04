"""
Weather feature builder — v3 implementation.

Per the locked v3 pre-registration document
(docs/PRE_REGISTRATION_v3.md, Section 7.4).

Takes a DataFrame of hourly atmospheric observations with columns:
    cape, temperature_2m, dewpoint_2m, pressure_msl,
    wind_speed_10m, wind_speed_80m, wind_speed_180m,
    precipitation

Returns the same DataFrame augmented with:
    - Derived atmospheric quantities (Section 7.3)
    - Seven structural features (Section 7.4) consumed by the v1 commitment formula
    - Coherence Tension (CT) and threshold flag

This implementation is verbatim against the locked v3 design document.
The commitment formula and lifecycle classification remain unchanged
from v1/v2 — those live in engine_service.run_pipeline. This file's
sole responsibility is mapping atmospheric inputs to structural
features per the registered specification.

Inputs are expected at hourly cadence. Several stages use 6-hour
rolling windows; with shorter input histories, those stages return
valid but noisier values per the locked spec.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def _clip01(s: pd.Series) -> pd.Series:
    return s.clip(0.0, 1.0)


def _lag1_autocorr(arr: np.ndarray) -> float:
    """Lag-1 Pearson autocorrelation of an array.

    Returns 0.0 if the array has fewer than 2 values or zero variance.
    """
    a = np.asarray(arr, dtype=float)
    a = a[~np.isnan(a)]
    if a.size < 2:
        return 0.0
    x = a[:-1]
    y = a[1:]
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    corr = np.corrcoef(x, y)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(corr)


# ---------------------------------------------------------------------------
# Main feature builder
# ---------------------------------------------------------------------------


def build_enriched_features_v3(df: pd.DataFrame) -> pd.DataFrame:
    """v3 feature builder — atmospheric inputs → structural features.

    Faithful implementation of Section 7.3 and 7.4 of the v3
    pre-registration. Adds the following columns to the input
    DataFrame and returns it:

        Derived atmospheric quantities:
            dewpoint_depression
            shear_proxy_60m
            shear_proxy_180m
            pressure_drop_3h
            cape_change_3h
            dewpoint_depression_change_3h
            precip_3h

        Structural features (Section 7.4):
            storm_intensity_score
            storm_transition_score
            phase_transition_score
            phase_prob_entropy
            ci_confidence
            stability
            reliability

        Compatibility (preserved from v2 for CT formula):
            phase_mix_score_3h

        Coherence Tension diagnostics (Section 7.7):
            CT
            CT_threshold
            CT_high
    """
    out = df.copy()

    # ---- Inputs ----
    cape = _safe_series(out, "cape", 0.0)
    temperature_2m = _safe_series(out, "temperature_2m", np.nan)
    dewpoint_2m = _safe_series(out, "dewpoint_2m", np.nan)
    pressure_msl = _safe_series(out, "pressure_msl", np.nan)
    wind_10 = _safe_series(out, "wind_speed_10m", 0.0)
    wind_80 = _safe_series(out, "wind_speed_80m", 0.0)
    wind_180 = _safe_series(out, "wind_speed_180m", 0.0)
    precipitation = _safe_series(out, "precipitation", 0.0)

    # ---- Section 7.3: Derived atmospheric quantities ----
    dewpoint_depression = (temperature_2m - dewpoint_2m).fillna(0.0)
    shear_proxy_60m = (wind_80 - wind_10).abs()
    shear_proxy_180m = (wind_180 - wind_10).abs()
    pressure_drop_3h = (-pressure_msl.diff(3)).fillna(0.0)
    cape_change_3h = cape.diff(3).fillna(0.0)
    dewpoint_depression_change_3h = dewpoint_depression.diff(3).fillna(0.0)
    precip_3h = precipitation.rolling(3, min_periods=1).mean()

    out["dewpoint_depression"] = dewpoint_depression
    out["shear_proxy_60m"] = shear_proxy_60m
    out["shear_proxy_180m"] = shear_proxy_180m
    out["pressure_drop_3h"] = pressure_drop_3h
    out["cape_change_3h"] = cape_change_3h
    out["dewpoint_depression_change_3h"] = dewpoint_depression_change_3h
    out["precip_3h"] = precip_3h

    # ---- Section 7.4: Structural features ----

    # storm_intensity_score
    cape_normalized = (cape / 2500.0).clip(0.0, 1.0)
    precip_normalized = (precip_3h / 5.0).clip(0.0, 1.0)
    out["storm_intensity_score"] = _clip01(
        0.65 * cape_normalized + 0.35 * precip_normalized
    )

    # storm_transition_score
    shear_normalized = (shear_proxy_180m / 15.0).clip(0.0, 1.0)
    pressure_drop_normalized = (pressure_drop_3h.abs() / 5.0).clip(0.0, 1.0)
    out["storm_transition_score"] = _clip01(
        0.50 * shear_normalized + 0.50 * pressure_drop_normalized
    )

    # phase_transition_score
    cape_rise = (cape_change_3h.clip(lower=0.0) / 1000.0).clip(0.0, 1.0)
    moisture_increase = (
        (-dewpoint_depression_change_3h).clip(lower=0.0) / 5.0
    ).clip(0.0, 1.0)
    pressure_rate = (
        (pressure_drop_3h - pressure_drop_3h.shift(3))
        .abs()
        .fillna(0.0)
        / 3.0
    ).clip(0.0, 1.0)
    out["phase_transition_score"] = _clip01(
        0.40 * cape_rise + 0.35 * moisture_increase + 0.25 * pressure_rate
    )

    # phase_prob_entropy (Section 7.4 — 6-hour window)
    window = 6
    cape_var = (
        cape.rolling(window, min_periods=2).std().fillna(0.0) / 500.0
    )
    ddep_var = (
        dewpoint_depression.rolling(window, min_periods=2).std().fillna(0.0) / 5.0
    )
    press_var = (
        pressure_msl.rolling(window, min_periods=2).std().fillna(0.0) / 5.0
    )
    out["phase_prob_entropy"] = _clip01(
        0.40 * cape_var + 0.35 * ddep_var + 0.25 * press_var
    )

    # ci_confidence
    out["ci_confidence"] = _clip01(1.0 - out["phase_prob_entropy"])

    # stability
    stability_raw = 1.0 / (
        1.0 + cape_change_3h.abs() / 500.0 + pressure_drop_3h.abs() / 3.0
    )
    out["stability"] = _clip01(stability_raw)

    # reliability — lag-1 autocorrelation over 6-hour window
    cape_lag1_corr = cape.rolling(window, min_periods=3).apply(
        _lag1_autocorr, raw=True
    ).fillna(0.0)
    pressure_lag1_corr = pressure_msl.rolling(window, min_periods=3).apply(
        _lag1_autocorr, raw=True
    ).fillna(0.0)
    reliability_raw = 0.5 + 0.5 * (
        0.6 * cape_lag1_corr + 0.4 * pressure_lag1_corr
    )
    out["reliability"] = _clip01(reliability_raw)

    # ---- v2-compatibility column for CT formula (preserved unchanged) ----
    # phase_mix_score_3h is computed from precip flag and temp flip, mirroring
    # the v2 feature builder's definition. Per Section 7.7, this column is
    # preserved as-is for CT compatibility; it is not part of v3's hypothesis
    # under test.
    precip_flag = (precipitation > 0.1).astype(float)
    temp_trend_3h = temperature_2m.diff(3).fillna(0.0)
    temp_flip = temp_trend_3h.diff().abs().fillna(0.0)
    temp_flip_norm = temp_flip / max(float(temp_flip.abs().max()), 1e-9)
    out["phase_mix_score_3h"] = _clip01(
        0.5 * precip_flag.rolling(3, min_periods=1).mean()
        + 0.5 * temp_flip_norm.abs().clip(0.0, 1.0)
    )

    # ---- Section 7.7: Coherence Tension (diagnostic, not verification target) ----
    out["CT"] = _compute_ct_v3(out)
    if out["CT"].notna().any():
        out["CT_threshold"] = float(np.nanquantile(out["CT"], 0.97))
    else:
        out["CT_threshold"] = 0.0
    out["CT_high"] = out["CT"] >= out["CT_threshold"]

    return out


def _compute_ct_v3(df: pd.DataFrame, eps: float = 1e-8) -> np.ndarray:
    """CT formula unchanged from v2 (Section 7.7)."""
    instability = (
        0.50 * df["phase_transition_score"].values
        + 0.30 * df["storm_transition_score"].values
        + 0.20 * df["storm_intensity_score"].values
    )
    competition = (
        0.70 * df["phase_prob_entropy"].values
        + 0.30 * df["phase_mix_score_3h"].values
    )
    persistence = (
        0.45 * df["stability"].values
        + 0.35 * df["reliability"].values
        + 0.20 * df["ci_confidence"].values