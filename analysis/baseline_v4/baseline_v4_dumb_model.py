"""
baseline_v4_dumb_model.py

Generic statistical baseline for v4 severe-weather pre-registration.
Companion to pre-registration-v4-baseline (PRE_REGISTRATION_v4_BASELINE.md).

Modes:
    setup        Pull training data, compute event_observed labels,
                 write CSV + SHA-256
    lock-fit     Fit primary + auxiliary models on locked training CSV,
                 save artifacts
    predict      Generate predictions over evaluation window (causal features)
    score        Compute per-regime reliability + Brier metrics
    compare      Apply v3.0-vs-baseline comparison criteria (Section 7)

Database connection uses these environment variables (with defaults):
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=dynametrix
    POSTGRES_PASSWORD=dynametrix
    POSTGRES_DB=dynametrix
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib
from sqlalchemy import create_engine, text

# ============================================================================
# CONFIGURATION (LOCKED BY PRE-REGISTRATION)
# ============================================================================

V4_LOCATIONS = {
    "Wichita, KS":    "29172590-f05d-483c-b213-b851421e47ff",
    "Omaha, NE":      "96ffa380-69ff-472e-9418-d981e695cf81",
    "Dodge City, KS": "7e37c63e-4cc2-4ea7-a539-c50fea99f683",
    "Nashville, TN":  "d76fc5a1-e2b9-4662-89b4-1b1499ff3201",
    "Louisville, KY": "a26d4e34-4baf-463b-af98-1d28c54e3b9d",
    "Cincinnati, OH": "3885e98e-966c-48f3-86af-d4386cbc6cb1",
}

PLAINS_LOCATIONS = ["Wichita, KS", "Omaha, NE", "Dodge City, KS"]
OHIO_VALLEY_LOCATIONS = ["Nashville, TN", "Louisville, KY", "Cincinnati, OH"]

ATMOS_DIRECT = [
    "cape",
    "temperature_2m", "dewpoint_2m", "relative_humidity_2m", "pressure_msl",
    "precipitation",
]

ATMOS_WIND_PAIRS = [
    ("wind_speed_10m", "wind_direction_10m", "u_10m", "v_10m"),
    ("wind_speed_80m", "wind_direction_80m", "u_80m", "v_80m"),
]

BASE_FEATURES = ATMOS_DIRECT + [
    comp for _, _, u, v in ATMOS_WIND_PAIRS for comp in (u, v)
]
assert len(BASE_FEATURES) == 10

ROLLING_WINDOWS = [3, 6, 12, 24]
DIFF_INTERVALS  = [1, 3, 6]

EVENT_TYPES_QUALIFYING = ("wind", "hail", "tornado")
MATCH_RADIUS_KM       = 50.0
LEAD_WINDOW_HOURS     = 48

N_BINS                = 10
BIN_MIN_SAMPLES       = 30
RELIABILITY_PASS_THRESHOLD = 6

COMPARISON_BSS_DELTA = 0.05


def get_engine():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "dynametrix")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "dynametrix")
    db   = os.environ.get("POSTGRES_DB", "dynametrix")
    url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    return create_engine(url, future=True)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_r = np.radians(lat1)
    lat2_r = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_interval(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def load_atmospheric(engine, location_ids, start_time=None, end_time=None):
    """Fetch atmospheric_observations rows for given locations / time window."""
    # Quote column names to preserve case in PostgreSQL.
    # Unquoted identifiers are folded to lowercase, which breaks the mixed-case
    # column names like "temperature_500hPa".
    cols_list = (
        ["location_id", "observed_at"] + ATMOS_DIRECT +
        [s for s, _, _, _ in ATMOS_WIND_PAIRS] +
        [d for _, d, _, _ in ATMOS_WIND_PAIRS]
    )
    cols_select = ", ".join(f'"{c}"' for c in cols_list)


    placeholders = ", ".join(f":id{i}" for i in range(len(location_ids)))
    params = {f"id{i}": loc for i, loc in enumerate(location_ids)}
    where = [f"location_id IN ({placeholders})"]
    if start_time is not None:
        where.append("observed_at >= :start_t")
        params["start_t"] = start_time
    if end_time is not None:
        where.append("observed_at < :end_t")
        params["end_t"] = end_time
    sql = f"SELECT {cols_select} FROM atmospheric_observations WHERE {' AND '.join(where)} ORDER BY location_id, observed_at"
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
    return df


def load_events(engine, start_time=None, end_time=None):
    where = []
    params = {}
    if start_time is not None:
        where.append("event_at >= :start_t")
        params["start_t"] = start_time
    if end_time is not None:
        where.append("event_at < :end_t")
        params["end_t"] = end_time
    types_ph = ", ".join(f":t{i}" for i in range(len(EVENT_TYPES_QUALIFYING)))
    where.append(f"event_type IN ({types_ph})")
    for i, t in enumerate(EVENT_TYPES_QUALIFYING):
        params[f"t{i}"] = t
    sql = f"SELECT event_at, latitude, longitude, event_type FROM ground_truth_events WHERE {' AND '.join(where)} ORDER BY event_at"
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    df["event_at"] = pd.to_datetime(df["event_at"], utc=True)
    return df


def load_locations(engine, location_ids):
    placeholders = ", ".join(f":id{i}" for i in range(len(location_ids)))
    params = {f"id{i}": loc for i, loc in enumerate(location_ids)}
    sql = f"SELECT id, label, latitude, longitude FROM locations WHERE id IN ({placeholders})"
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df


def compute_event_observed(atmos_df, events_df, locations_df):
    # Build lookup with str-typed keys.
    # psycopg2 returns location_id as a UUID object; we coerce to str so the
    # lookup matches the str(row.location_id) used below for every atmos row.
    loc_lookup = {
        str(row.id): {"latitude": row.latitude, "longitude": row.longitude}
        for row in locations_df.itertuples(index=False)
    }

    labels = np.zeros(len(atmos_df), dtype=int)
    if len(events_df) == 0:
        return labels
    event_at = events_df["event_at"].values
    event_lat = events_df["latitude"].values
    event_lon = events_df["longitude"].values
    for idx, row in enumerate(atmos_df.itertuples(index=False)):
        loc_id = str(row.location_id)
        if loc_id not in loc_lookup:
            continue
        loc_lat = loc_lookup[loc_id]["latitude"]
        loc_lon = loc_lookup[loc_id]["longitude"]
        t0 = row.observed_at
        t1 = t0 + pd.Timedelta(hours=LEAD_WINDOW_HOURS)
        in_window = (event_at >= np.datetime64(t0)) & (event_at < np.datetime64(t1))
        if not in_window.any():
            continue
        d = haversine_km(loc_lat, loc_lon, event_lat[in_window], event_lon[in_window])
        if (d <= MATCH_RADIUS_KM).any():
            labels[idx] = 1
    return labels


def decompose_winds(df):
    df = df.copy()
    for speed_col, dir_col, u_col, v_col in ATMOS_WIND_PAIRS:
        rad = np.radians(df[dir_col].astype(float))
        df[u_col] = df[speed_col].astype(float) * np.sin(rad)
        df[v_col] = df[speed_col].astype(float) * np.cos(rad)
    drop_cols = [s for s, _, _, _ in ATMOS_WIND_PAIRS] + [d for _, d, _, _ in ATMOS_WIND_PAIRS]
    df = df.drop(columns=drop_cols)
    return df


def build_features(df):
    df = df.sort_values(["location_id", "observed_at"]).reset_index(drop=True)
    pieces = [df[["location_id", "observed_at"] + BASE_FEATURES].copy()]
    grp = df.groupby("location_id")
    for window in ROLLING_WINDOWS:
        for base in BASE_FEATURES:
            mean_series = grp[base].rolling(window=window, min_periods=1).mean().reset_index(0, drop=True)
            std_series  = grp[base].rolling(window=window, min_periods=2).std().reset_index(0, drop=True)
            pieces.append(mean_series.rename(f"{base}_mean_{window}h").to_frame())
            pieces.append(std_series.rename(f"{base}_std_{window}h").to_frame())
    for interval in DIFF_INTERVALS:
        for base in BASE_FEATURES:
            diff_series = grp[base].diff(periods=interval)
            pieces.append(diff_series.rename(f"{base}_diff_{interval}h").to_frame())
    return pd.concat(pieces, axis=1)


def get_feature_columns():
    cols = list(BASE_FEATURES)
    for w in ROLLING_WINDOWS:
        for b in BASE_FEATURES:
            cols.append(f"{b}_mean_{w}h")
            cols.append(f"{b}_std_{w}h")
    for i in DIFF_INTERVALS:
        for b in BASE_FEATURES:
            cols.append(f"{b}_diff_{i}h")
    assert len(cols) == 120, f"Expected 120 features, got {len(cols)}"
    return cols


def cmd_setup(args):
    print("=" * 72)
    print("BASELINE v4 - SETUP MODE")
    print("=" * 72)
    if args.end_time:
        end_time = pd.Timestamp(args.end_time, tz="UTC")
    else:
        end_time = pd.Timestamp.now(tz="UTC")
    print(f"Training-data cutoff: {end_time.isoformat()}")
    engine = get_engine()
    v4_ids = set(V4_LOCATIONS.values())
    with engine.connect() as conn:
        all_locs_df = pd.read_sql(text("SELECT id, label FROM locations ORDER BY label"), conn)
    all_locs_df["id"] = all_locs_df["id"].astype(str)
    training_locs = all_locs_df[~all_locs_df["id"].isin(v4_ids)]
    training_loc_ids = training_locs["id"].tolist()
    print(f"\nIdentified {len(training_loc_ids)} training locations (existing v3 set):")
    for _, row in training_locs.iterrows():
        print(f"  {row['label']}: {row['id']}")
    print(f"\nStep 1/4: Loading atmospheric observations...")
    atmos = load_atmospheric(engine, training_loc_ids, end_time=end_time)
    print(f"  Loaded {len(atmos)} atmospheric observation rows")
    if len(atmos) == 0:
        print("ERROR: No atmospheric observations found for training locations.")
        sys.exit(1)
    print(f"\nStep 2/4: Loading ground-truth events...")
    events = load_events(
        engine,
        start_time=atmos["observed_at"].min(),
        end_time=end_time + pd.Timedelta(hours=LEAD_WINDOW_HOURS),
    )
    print(f"  Loaded {len(events)} qualifying ground-truth events")
    print(f"\nStep 3/4: Loading location coordinates...")
    locs = load_locations(engine, training_loc_ids)
    print(f"\nStep 4/4: Computing event_observed labels (slow part)...")
    atmos["event_observed"] = compute_event_observed(atmos, events, locs)
    pos = int(atmos["event_observed"].sum())
    rate = 100.0 * pos / len(atmos) if len(atmos) > 0 else 0.0
    print(f"  Computed {len(atmos)} labels; {pos} positive ({rate:.2f}%)")
    print("\nDecomposing wind variables (speed/direction -> u/v)...")
    atmos = decompose_winds(atmos)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "baseline_v4_training_set.csv"
    atmos.to_csv(csv_path, index=False)
    print(f"\nWrote {csv_path}")
    sha = sha256_of_file(csv_path)
    hash_path = out / "baseline_v4_training_set_sha256.txt"
    with open(hash_path, "w") as f:
        f.write(sha + "\n")
    print(f"Wrote {hash_path}")
    print()
    print("=" * 72)
    print("SETUP COMPLETE")
    print("=" * 72)
    print(f"  Training rows: {len(atmos)}")
    print(f"  Positive rate: {rate:.2f}%")
    print(f"  SHA-256:       {sha}")
    print()
    print("FILL THIS VALUE INTO PRE_REGISTRATION_v4_BASELINE.md Section 9:")
    print(f"  Training set SHA-256: {sha}")


def cmd_lock_fit(args):
    print("=" * 72)
    print("BASELINE v4 - LOCK-FIT MODE")
    print("=" * 72)
    out = Path(args.output_dir)
    csv_path = out / "baseline_v4_training_set.csv"
    hash_path = out / "baseline_v4_training_set_sha256.txt"
    if not csv_path.exists() or not hash_path.exists():
        print(f"ERROR: training set or hash file missing. Run 'setup' first.")
        sys.exit(1)
    with open(hash_path) as f:
        locked_sha = f.read().strip()
    print(f"\nVerifying training set hash...")
    actual_sha = sha256_of_file(csv_path)
    if actual_sha != locked_sha:
        print(f"ERROR: hash mismatch.")
        sys.exit(1)
    print(f"  OK: {locked_sha[:16]}...")
    print(f"\nLoading training data and building features...")
    df = pd.read_csv(csv_path, parse_dates=["observed_at"])
    feats = build_features(df)
    cols = get_feature_columns()
    X = feats[cols]
    y = df["event_observed"].values
    valid_mask = ~X.isna().any(axis=1)
    X = X[valid_mask].values
    y = y[valid_mask]
    print(f"  Valid training rows after NaN drop: {len(X)} (of {len(df)})")
    print(f"  Positive rate: {100*y.sum()/len(y):.2f}%")
    print(f"  Feature count: {X.shape[1]}")
    print(f"\nFitting primary model (StandardScaler + logistic regression with CV C selection)...")
    primary = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegressionCV(
            Cs=10, cv=5, scoring="roc_auc",
            max_iter=2000, penalty="l2", solver="lbfgs",
            n_jobs=-1, random_state=42,
        )),
    ])
    primary.fit(X, y)
    clf = primary.named_steps["clf"]
    cv_aucs = np.mean(clf.scores_[1], axis=0)
    print(f"  Selected C:               {clf.C_[0]:.4f}")
    print(f"  Cross-val ROC-AUC (max):  {cv_aucs.max():.4f}")
    print(f"\nFitting auxiliary model (gradient-boosted tree)...")
    auxiliary = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42,
    )
    auxiliary.fit(X, y)
    print(f"  Fitted: {auxiliary.n_estimators} trees, depth {auxiliary.max_depth}")
    primary_path = out / "baseline_v4_primary_model.joblib"
    aux_path = out / "baseline_v4_auxiliary_model.joblib"
    meta_path = out / "baseline_v4_model_metadata.json"
    joblib.dump(primary, primary_path)
    joblib.dump(auxiliary, aux_path)
    meta = {
        "primary_model_class": "Pipeline(StandardScaler + LogisticRegressionCV)",
        "primary_C_selected": float(clf.C_[0]),
        "primary_cv_roc_auc_max": float(cv_aucs.max()),
        "auxiliary_model_class": "GradientBoostingClassifier",
        "auxiliary_n_estimators": 200,
        "auxiliary_max_depth": 4,
        "auxiliary_learning_rate": 0.05,
        "feature_count": int(X.shape[1]),
        "training_rows": int(len(y)),
        "training_positive_rate": float(y.sum() / len(y)),
        "training_set_sha256": locked_sha,
        "random_state": 42,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nWrote {primary_path}")
    print(f"Wrote {aux_path}")
    print(f"Wrote {meta_path}")


def cmd_predict(args):
    print("=" * 72)
    print("BASELINE v4 - PREDICT MODE")
    print("=" * 72)
    out = Path(args.output_dir)
    primary_path = out / "baseline_v4_primary_model.joblib"
    aux_path = out / "baseline_v4_auxiliary_model.joblib"
    if not primary_path.exists():
        print(f"ERROR: {primary_path} not found. Run 'lock-fit' first.")
        sys.exit(1)
    start_t = pd.Timestamp(args.start_time, tz="UTC")
    end_t = pd.Timestamp(args.end_time, tz="UTC")
    print(f"Evaluation window: {start_t.isoformat()} to {end_t.isoformat()}")
    primary = joblib.load(primary_path)
    auxiliary = joblib.load(aux_path)
    engine = get_engine()
    lookback = max(ROLLING_WINDOWS) + max(DIFF_INTERVALS) + 1
    atmos_start = start_t - pd.Timedelta(hours=lookback)
    print(f"Loading atmospheric data with {lookback}h lookback...")
    atmos = load_atmospheric(engine, list(V4_LOCATIONS.values()), start_time=atmos_start, end_time=end_t)
    print(f"  {len(atmos)} observations loaded")
    print("Decomposing winds and building features...")
    atmos = decompose_winds(atmos)
    feats = build_features(atmos)
    cols = get_feature_columns()
    eval_mask = (feats["observed_at"] >= start_t) & (feats["observed_at"] < end_t)
    eval_df = feats[eval_mask].copy()
    X = eval_df[cols]
    valid_mask = ~X.isna().any(axis=1)
    eval_df = eval_df[valid_mask]
    X = X[valid_mask].values
    print(f"  {len(eval_df)} predictions to generate")
    if len(eval_df) == 0:
        print("WARNING: No valid evaluation rows.")
        return
    primary_probs = primary.predict_proba(X)[:, 1]
    aux_probs = auxiliary.predict_proba(X)[:, 1]
    out_df = eval_df[["location_id", "observed_at"]].copy()
    out_df["primary_prob"] = primary_probs
    out_df["auxiliary_prob"] = aux_probs
    pred_path = out / "baseline_v4_predictions.csv"
    out_df.to_csv(pred_path, index=False)
    print(f"\nWrote {pred_path}")


def compute_regime_metrics(predictions, outcomes, prob_col):
    merged = predictions.merge(outcomes, on=["location_id", "observed_at"], how="inner")
    regime_lookup = {}
    for label, loc_id in V4_LOCATIONS.items():
        regime_lookup[str(loc_id)] = "Plains" if label in PLAINS_LOCATIONS else "Ohio Valley"
    merged["regime"] = merged["location_id"].astype(str).map(regime_lookup)
    results = {}
    for regime in ("Plains", "Ohio Valley"):
        sub = merged[merged["regime"] == regime]
        if len(sub) == 0:
            results[regime] = {"error": "no_data"}
            continue
        probs = sub[prob_col].values
        y = sub["event_observed"].values
        base = float(y.mean())
        brier = float(np.mean((probs - y) ** 2))
        brier_clim = float(np.mean((base - y) ** 2))
        bss = float(1 - brier / brier_clim) if brier_clim > 0 else float("nan")
        edges = np.linspace(0.0, 1.0, N_BINS + 1)
        assign = np.clip(np.digitize(probs, edges) - 1, 0, N_BINS - 1)
        passed = 0
        included = 0
        bins_info = []
        for i in range(N_BINS):
            m = assign == i
            n = int(m.sum())
            info = {"bin": i, "range": f"[{edges[i]:.2f},{edges[i+1]:.2f})", "n": n}
            if n < BIN_MIN_SAMPLES:
                info["excluded"] = True
                if n > 0:
                    info["mean_pred"] = float(probs[m].mean())
                    info["observed_freq"] = float(y[m].mean())
            else:
                included += 1
                mp = float(probs[m].mean())
                k = int(y[m].sum())
                of = float(k / n)
                lo, hi = wilson_interval(k, n)
                passes = bool(lo <= mp <= hi)
                if passes:
                    passed += 1
                info.update({
                    "mean_pred": mp,
                    "observed_freq": of,
                    "wilson_lo": float(lo),
                    "wilson_hi": float(hi),
                    "passes": passes,
                })
            bins_info.append(info)
        reliability_pass = passed >= RELIABILITY_PASS_THRESHOLD
        skill_pass = bss > 0
        if reliability_pass and skill_pass:
            outcome = "calibrated_and_skilled"
        elif skill_pass and not reliability_pass:
            outcome = "skilled_but_miscalibrated"
        elif reliability_pass and not skill_pass:
            outcome = "calibrated_but_no_skill"
        else:
            outcome = "not_calibrated_and_not_skilled"
        results[regime] = {
            "n_predictions": int(len(probs)),
            "n_positive": int(y.sum()),
            "base_rate": base,
            "brier": brier,
            "brier_climat": brier_clim,
            "bss": bss,
            "included_bins": included,
            "passed_bins": passed,
            "reliability_pass": bool(reliability_pass),
            "skill_pass": bool(skill_pass),
            "regime_outcome": outcome,
            "bins": bins_info,
        }
    plains_ok = results["Plains"].get("regime_outcome") == "calibrated_and_skilled"
    ov_ok = results["Ohio Valley"].get("regime_outcome") == "calibrated_and_skilled"
    if plains_ok and ov_ok:
        overall = "REGIME-GENERAL"
    elif plains_ok and not ov_ok:
        overall = "PLAINS-ONLY"
    elif ov_ok and not plains_ok:
        overall = "OHIO VALLEY ONLY"
    else:
        overall = "NEITHER"
    results["overall_outcome"] = overall
    return results


def cmd_score(args):
    print("=" * 72)
    print("BASELINE v4 - SCORE MODE")
    print("=" * 72)
    out = Path(args.output_dir)
    pred_path = out / "baseline_v4_predictions.csv"
    if not pred_path.exists():
        print(f"ERROR: {pred_path} not found. Run 'predict' first.")
        sys.exit(1)
    preds = pd.read_csv(pred_path, parse_dates=["observed_at"])
    print(f"Loaded {len(preds)} predictions")
    engine = get_engine()
    start_t = preds["observed_at"].min()
    end_t = preds["observed_at"].max() + pd.Timedelta(hours=LEAD_WINDOW_HOURS + 1)
    events = load_events(engine, start_time=start_t, end_time=end_t)
    print(f"Loaded {len(events)} ground-truth events in window")
    locs = load_locations(engine, list(V4_LOCATIONS.values()))
    print("Computing event_observed labels for predictions...")
    preds["event_observed"] = compute_event_observed(preds, events, locs)
    outcomes = preds[["location_id", "observed_at", "event_observed"]]
    print("\nPrimary model metrics:")
    primary_res = compute_regime_metrics(preds, outcomes, "primary_prob")
    print("\nAuxiliary model metrics:")
    aux_res = compute_regime_metrics(preds, outcomes, "auxiliary_prob")
    summary = {"primary": primary_res, "auxiliary": aux_res}
    summary_path = out / "baseline_v4_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nWrote {summary_path}")
    for label, res in (("PRIMARY (LOGISTIC REGRESSION)", primary_res),
                       ("AUXILIARY (GRADIENT-BOOSTED TREE)", aux_res)):
        print()
        print("=" * 72)
        print(f"BASELINE v4 OUTCOME - {label}")
        print("=" * 72)
        for regime in ("Plains", "Ohio Valley"):
            r = res[regime]
            if "error" in r:
                print(f"  {regime}: no data"); continue
            print(f"  {regime}:")
            print(f"    n predictions: {r['n_predictions']}")
            print(f"    base rate:     {r['base_rate']:.4f}")
            print(f"    BSS:           {r['bss']:+.4f}")
            print(f"    Bins passed:   {r['passed_bins']} of {r['included_bins']} included")
            print(f"    Outcome:       {r['regime_outcome']}")
        print(f"\n  OVERALL: {res['overall_outcome']}")


def cmd_compare(args):
    print("=" * 72)
    print("BASELINE v4 - COMPARE MODE")
    print("=" * 72)
    print()
    print("Requires both v4 and v4-baseline result documents to be locked.")
    print("Comparison criterion (PRE_REGISTRATION_v4_BASELINE.md Section 7.1):")
    print(f"  v3.0 ADDS SIGNAL if:")
    print(f"    (a) Per-regime BSS exceeds baseline by ΔBSS > {COMPARISON_BSS_DELTA} in >=1 regime")
    print(f"    (b) Reliability not worse than baseline in any regime")


def main():
    p = argparse.ArgumentParser(description="Baseline v4 - generic statistical model on raw atmospheric inputs")
    p.add_argument("--output-dir", default=".", help="Output directory (default: current)")
    sub = p.add_subparsers(dest="mode")
    sp = sub.add_parser("setup", help="Pull training data, compute labels, write CSV")
    sp.add_argument("--end-time", help="Training cutoff time (ISO 8601 UTC); default: now")
    sub.add_parser("lock-fit", help="Fit models on locked training set")
    sp = sub.add_parser("predict", help="Generate predictions over evaluation window")
    sp.add_argument("--start-time", required=True, help="ISO 8601 UTC")
    sp.add_argument("--end-time", required=True, help="ISO 8601 UTC")
    sub.add_parser("score", help="Compute per-regime metrics")
    sub.add_parser("compare", help="v3.0 vs baseline comparison")
    args = p.parse_args()
    if args.mode == "setup":
        cmd_setup(args)
    elif args.mode == "lock-fit":
        cmd_lock_fit(args)
    elif args.mode == "predict":
        cmd_predict(args)
    elif args.mode == "score":
        cmd_score(args)
    elif args.mode == "compare":
        cmd_compare(args)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()