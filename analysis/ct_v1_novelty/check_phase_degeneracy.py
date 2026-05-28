"""Verify the phase-classifier degeneracy hypothesis: how often is the precipitation
activity factor zero in the comparison subset, and what does the distribution of
CT-v1 values look like?"""
import sys; sys.path.insert(0, 'backend')
sys.path.insert(0, 'analysis/ct_v1_novelty')
from app.db.session import SessionLocal
from app.db.models.engine import AtmosphericObservation
from sqlalchemy import select
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Load comparison-window atmospheric data
with SessionLocal() as db:
    cols = ["location_id", "observed_at", "precipitation", "temperature_2m", "dewpoint_2m"]
    stmt = select(*[getattr(AtmosphericObservation, c) for c in cols]).where(
        AtmosphericObservation.observed_at >= datetime(2026, 5, 15, tzinfo=timezone.utc)
    )
    rows = db.execute(stmt).all()

df = pd.DataFrame(rows, columns=cols)
df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)

print(f"Comparison-subset atmospheric observations: {len(df):,} cells\n")

# Precipitation distribution
print("Precipitation rate distribution (mm/h):")
print(f"  fraction with precip < 0.01: {(df['precipitation'] < 0.01).mean():.4f}")
print(f"  fraction with precip < 0.10: {(df['precipitation'] < 0.10).mean():.4f}  (alpha = 0)")
print(f"  fraction with precip < 1.10: {(df['precipitation'] < 1.10).mean():.4f}  (alpha < 1)")
print(f"  fraction with precip >= 0.10: {(df['precipitation'] >= 0.10).mean():.4f}  (alpha > 0)")
print(f"  mean precip: {df['precipitation'].mean():.4f}")
print(f"  median precip: {df['precipitation'].median():.4f}")
print(f"  95th pct precip: {df['precipitation'].quantile(0.95):.4f}")
print(f"  99th pct precip: {df['precipitation'].quantile(0.99):.4f}")
print(f"  max precip: {df['precipitation'].max():.4f}")
print()

# Alpha (precipitation activity factor) distribution
alpha = ((df["precipitation"] - 0.1) / 1.0).clip(0.0, 1.0)
print(f"Alpha distribution:")
print(f"  fraction with alpha = 0: {(alpha == 0).mean():.4f}")
print(f"  fraction with 0 < alpha < 1: {((alpha > 0) & (alpha < 1)).mean():.4f}")
print(f"  fraction with alpha = 1: {(alpha == 1).mean():.4f}")
print()

# Phase distribution in active-precip cells
active = df[df["precipitation"] >= 0.1].copy()
if len(active) > 0:
    active["T_w"] = active["temperature_2m"] - (active["temperature_2m"] - active["dewpoint_2m"]) / 3.0
    print(f"In {len(active):,} active-precip cells:")
    print(f"  T_w range: {active['T_w'].min():.2f} to {active['T_w'].max():.2f} °C")
    print(f"  fraction T_w < 0: {(active['T_w'] < 0).mean():.4f}")
    print(f"  fraction T_w in [0, 4]: {((active['T_w'] >= 0) & (active['T_w'] <= 4)).mean():.4f}")
    print(f"  fraction T_w > 4: {(active['T_w'] > 4).mean():.4f}")
