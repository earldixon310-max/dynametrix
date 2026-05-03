"""
Weather feature builder — v1 implementation of the MCC/CI/CSO weather
structural feature pipeline.

Takes a DataFrame of hourly weather observations with columns:
    precip_mm, surface_pressure_hPa, temp_C

Returns the same DataFrame augmented with the structural feature
columns that engine_service.run_pipeline consumes:

    phase_prob_entropy
    storm_transition_score
    storm_intensity_score
    phase_transition_score
    ci_confidence
    stability
    reliability
    pressure_drop_3h
    temp_trend_3h
    phase_mix_score_3h
    phase_mix_score_6h
    phase_transition_raw
    phase_transition_z
    CT
    CT_threshold
    CT_high

Inputs are expected at hourly cadence. The 24-hour rolling z-score in
phase_transition relies on at least ~24 hours of history; with shorter
inputs it returns valid but noisier values.

This is the v1 weather feature builder; the implementation is unchanged
from the original feature_builder.py. The only modifications are:
  - production module-level docstring
  - explicit type imports
  - removed duplicate `import pandas as pd`
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def _robust_zscore(series: pd.Series, window: int = 24) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    minp = max(5, window // 3)
    med = s.rolling(window, min_periods=minp).median()
    mad = (s - med).abs().rolling(window, min_periods=minp).median()
    z = (s - med) / (1.4826 * mad.replace(0, np.nan))
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _normalize_01(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    max_abs = float(s.abs().max())
    if max_abs <= 1e-9:
        return pd.Series(0.0, index=s.index, dtype=float)
    return (s / max_abs).clip(-1.0, 1.0)


def build_enriched_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    precip = _safe_series(out, "precip_mm", 0.0)
    pressure = _safe_series(out, "surface_pressure_hPa", np.nan)
    temp = _safe_series(out, "temp_C", np.nan)

    # -----------------------------
    # Basic weather structure proxies
    # -----------------------------
    out["phase_prob_entropy"] = 0.0
    out["storm_transition_score"] = 0.0
    out["storm_intensity_score"] = 0.0
    out["phase_transition_score"] = 0.0
    out["ci_confidence"] = 0.0
    out["stability"] = 0.0
    out["reliability"] = 0.0

    if "precip_mm" in out.columns:
        out["storm_intensity_score"] = precip.rolling(3, min_periods=1).mean()

    if "surface_pressure_hPa" in out.columns:
        out["pressure_drop_3h"] = (-pressure.diff(3)).fillna(0.0)
    else:
        out["pressure_drop_3h"] = 0.0

    if "temp_C" in out.columns:
        out["temp_trend_3h"] = temp.diff(3).fillna(0.0)
    else:
        out["temp_trend_3h"] = 0.0

    # -----------------------------
    # Storm transition proxy
    # -----------------------------
    storm_raw = out["pressure_drop_3h"].fillna(0.0)
    out["storm_transition_score"] = _normalize_01(storm_raw.abs())

    # -----------------------------
    # CI / stability / reliability proxies
    # -----------------------------
    ci_raw = storm_raw.abs().rolling(3, min_periods=1).mean()
    out["ci_confidence"] = _normalize_01(ci_raw).clip(0.0, 1.0)
    out["stability"] = (1.0 / (1.0 + storm_raw.abs().fillna(0.0))).clip(0.0, 1.0)
    reliability_raw = out["ci_confidence"].rolling(3, min_periods=1).mean()
    out["reliability"] = _normalize_01(reliability_raw).clip(0.0, 1.0)

    # -----------------------------
    # Lightweight entropy / phase-mix proxies
    # -----------------------------
    precip_flag = (precip > 0.1).astype(float)
    temp_flip = out["temp_trend_3h"].diff().abs().fillna(0.0)
    press_var = out["pressure_drop_3h"].abs().fillna(0.0)

    entropy_raw = (
        0.45 * precip_flag.rolling(3, min_periods=1).mean()
        + 0.30 * _normalize_01(temp_flip.abs()).abs()
        + 0.25 * _normalize_01(press_var.abs()).abs()
    )
    out["phase_prob_entropy"] = entropy_raw.clip(0.0, 1.0)

    out["phase_mix_score_3h"] = (
        0.5 * precip_flag.rolling(3, min_periods=1).mean()
        + 0.5 * _normalize_01(temp_flip).abs()
    ).clip(0.0, 1.0)
    out["phase_mix_score_6h"] = (
        out["phase_mix_score_3h"].rolling(2, min_periods=1).mean()
    ).clip(0.0, 1.0)

    # -----------------------------
    # NEW phase transition engine
    # Fires on structural change, not level
    # -----------------------------
    ci = out["ci_confidence"]
    stability = out["stability"]
    reliability = out["reliability"]
    entropy = out["phase_prob_entropy"]
    mix3 = out["phase_mix_score_3h"]
    mix6 = out["phase_mix_score_6h"]
    phase_mix = pd.concat([mix3, mix6], axis=1).max(axis=1)

    ci_diff = ci.diff().fillna(0.0)
    stability_diff = stability.diff().fillna(0.0)
    reliability_diff = reliability.diff().fillna(0.0)
    entropy_diff = entropy.diff().fillna(0.0)
    mix_diff = phase_mix.diff().fillna(0.0)

    ci_slope = ci_diff.abs()
    stability_drop = (-stability_diff).clip(lower=0.0)
    reliability_drop = (-reliability_diff).clip(lower=0.0)
    entropy_rise = entropy_diff.clip(lower=0.0)
    mix_rise = mix_diff.clip(lower=0.0)

    ci_accel = ci_slope.diff().abs().fillna(0.0)
    entropy_accel = entropy_rise.diff().clip(lower=0.0).fillna(0.0)

    raw_transition = (
        0.28 * ci_slope
        + 0.24 * stability_drop
        + 0.18 * reliability_drop
        + 0.14 * entropy_rise
        + 0.10 * mix_rise
        + 0.04 * ci_accel
        + 0.02 * entropy_accel
    )

    raw_transition_smooth = raw_transition.rolling(3, min_periods=1).mean()
    transition_z = _robust_zscore(raw_transition_smooth, window=24)
    transition_score = (transition_z.clip(lower=0.0) / 3.0).clip(0.0, 1.0)

    # Context gate so transitions matter more when weather structure is already active
    context_gate = (
        0.6 * out["ci_confidence"] + 0.4 * out["storm_transition_score"]
    ).clip(0.0, 1.0)

    out["phase_transition_raw"] = raw_transition_smooth
    out["phase_transition_z"] = transition_z
    out["phase_transition_score"] = (
        transition_score * (0.5 + 0.5 * context_gate)
    ).clip(0.0, 1.0)

    # -----------------------------
    # Coherence Tension (CT)
    # -----------------------------
    out["CT"] = compute_ct_storm(out)

    # Threshold (robust high-percentile)
    out["CT_threshold"] = np.nanquantile(out["CT"], 0.97)

    # High-CT flag
    out["CT_high"] = out["CT"] >= out["CT_threshold"]

    return out


def compute_ct_storm(df: pd.DataFrame, eps: float = 1e-8) -> np.ndarray:
    instability = (
        0.50 * df["phase_transition_score"].values +
        0.30 * df["storm_transition_score"].values +
        0.20 * df["storm_intensity_score"].values
    )
    competition = (
        0.70 * df["phase_prob_entropy"].values +
        0.30 * df["phase_mix_score_3h"].values
    )
    persistence = (
        0.45 * df["stability"].values +
        0.35 * df["reliability"].values +
        0.20 * df["ci_confidence"].values
    )
    persistence = np.clip(persistence, 0.05, None)
    ct = (instability * competition) / np.sqrt(persistence + eps)
    return ct