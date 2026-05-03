"""
Engine integration layer.

The structural detection engine lives in the existing tools/ folder. We don't
re-implement it here; we shell out to those scripts and read their CSV outputs.

Wrapped scripts (per spec section 11):
- tools/run_live_open_meteo_pipeline.py
- tools/train_weather_commitment_calibrator.py
- tools/weather_commitment_calibrated.csv
- tools/ci_structural_signatures_app.csv
- tools/alerts.py

Real engine I/O contracts are documented in docs/ENGINE_INTEGRATION.md. The
stub implementations in `backend/tools/` let the scaffold boot end-to-end.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import random
import pandas as pd
import numpy as np

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.engine import AtmosphericObservation
from app.services.feature_builder import build_enriched_features

settings = get_settings()
log = get_logger(__name__)


@dataclass
class CalibratedRow:
    observed_at: datetime
    commitment_probability: float
    expected_lead_hours: Optional[float]
    event_type_calibrated: Optional[str]
    confidence: float
    lifecycle_state: str


class EngineError(RuntimeError):
    pass


class EngineService:
    """
    Thin wrapper. Each method documents the script signature it expects.
    Substitute the real implementations by dropping the engine files into
    `backend/tools/` (or mounting them via Docker) — the wrappers are stable.
    """

    def __init__(self, tools_dir: Optional[str] = None):
        self.tools_dir = Path(tools_dir or settings.ENGINE_TOOLS_DIR)
        if not self.tools_dir.exists():
            log.warning("engine.tools_dir_missing", path=str(self.tools_dir))

    # ---------- Pipeline ----------

    def run_pipeline(
        self,
        db: Session,
        location_id: UUID,
        output_csv: str,
        history_hours: int = 96,
    ) -> int:
        """v2 pipeline — pulls real atmospheric observations for a
        location and runs the v1 feature builder + commitment formula
        against them.

        Inputs:
            db:           SQLAlchemy session.
            location_id:  UUID of the location to evaluate.
            output_csv:   path to write the calibrated output row.
            history_hours: how far back to pull observations, default 96.

        Returns the number of output rows written (0 or 1).
        """
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=history_hours)

        # Pull recent past atmospheric observations, oldest first.
        observations = list(
            db.scalars(
                select(AtmosphericObservation)
                .where(
                    AtmosphericObservation.location_id == location_id,
                    AtmosphericObservation.observed_at >= cutoff,
                    AtmosphericObservation.observed_at <= now_utc,
                )
                .order_by(AtmosphericObservation.observed_at.asc())
            )
        )

        # Feature builder needs at least ~8 contiguous hours for its
        # 24-hour rolling z-scores to produce meaningful values.
        if len(observations) < 8:
            log.warning(
                "engine.insufficient_atmospheric_history",
                location_id=str(location_id),
                hours_available=len(observations),
            )
            empty = pd.DataFrame(columns=[
                "observed_at", "commitment_probability", "expected_lead_hours",
                "event_type_calibrated", "confidence", "lifecycle_state",
                "persistence", "coherence_energy", "trajectory_velocity",
            ])
            empty.to_csv(output_csv, index=False)
            return 0

        # Build the DataFrame with the column names the feature builder expects.
        # pressure_msl is sea-level-adjusted; the framework uses pressure
        # CHANGES, which are equivalent for surface vs MSL pressure for a
        # fixed location.
        df = pd.DataFrame([
            {
                "observed_at": o.observed_at,
                "precip_mm": o.precipitation if o.precipitation is not None else 0.0,
                "surface_pressure_hPa": o.pressure_msl,
                "temp_C": o.temperature_2m,
            }
            for o in observations
        ])

        # Run the structural feature builder.
        enriched = build_enriched_features(df)

        # Take the most recent (last) row's structural features.
        latest = enriched.iloc[-1]

        phase = float(latest["phase_transition_score"])
        transition = float(latest["storm_transition_score"])
        intensity = float(latest["storm_intensity_score"])
        entropy = float(latest["phase_prob_entropy"])
        ci = float(latest["ci_confidence"])
        stability = float(latest["stability"])
        reliability = float(latest["reliability"])

        # v1 commitment formula (unchanged from calibrator-v1.0).
        organization = (
            0.35 * phase +
            0.25 * transition +
            0.20 * intensity +
            0.10 * entropy +
            0.10 * ci
        )
        commitment_probability = float(np.clip(0.18 + 0.70 * organization, 0.05, 0.95))
        confidence = float(np.clip(
            0.25 + 0.35 * ci + 0.20 * reliability + 0.20 * stability, 0.05, 0.95
        ))

        # Lifecycle classification (unchanged).
        if commitment_probability >= 0.68:
            lifecycle_state = "commitment"
            expected_lead_hours = 6.0
        elif commitment_probability >= 0.50:
            lifecycle_state = "pre_commitment"
            expected_lead_hours = 12.0
        elif phase > 0.65 and transition > 0.25:
            lifecycle_state = "reconfiguration"
            expected_lead_hours = None
        elif commitment_probability < 0.30:
            lifecycle_state = "decay"
            expected_lead_hours = None
        else:
            lifecycle_state = "quiet"
            expected_lead_hours = None

        # Derived display metrics (unchanged).
        persistence = float(np.clip(
            (stability + reliability + ci) / 3.0,
            0.0, 1.0
        ))
        coherence_energy = float(np.clip(
            (0.45 * phase) +
            (0.25 * transition) +
            (0.15 * intensity) +
            (0.15 * ci),
            0.0, 1.0
        ))
        trajectory_velocity = float(np.clip(
            abs(coherence_energy - persistence),
            0.0, 1.0
        ))

        observed_at = pd.to_datetime(latest["observed_at"], utc=True).isoformat()

        out = pd.DataFrame([{
            "observed_at": observed_at,
            "commitment_probability": commitment_probability,
            "expected_lead_hours": expected_lead_hours,
            "event_type_calibrated": lifecycle_state,
            "confidence": confidence,
            "lifecycle_state": lifecycle_state,
            "persistence": persistence,
            "coherence_energy": coherence_energy,
            "trajectory_velocity": trajectory_velocity,
        }])

        out.to_csv(output_csv, index=False)
        return len(out)

        def val(name: str, default: float = 0.0) -> float:
            try:
                x = latest.get(name, default)
                if pd.isna(x):
                    return default
                return float(x)
            except Exception:
                return default

        transition = val("storm_transition_score")
        phase = val("phase_transition_score")
        intensity = val("storm_intensity_score")
        entropy = val("phase_prob_entropy")
        ci = val("ci_confidence")
        stability = val("stability")
        reliability = val("reliability")

        organization = (
            0.35 * phase +
            0.25 * transition +
            0.20 * intensity +
            0.10 * entropy +
            0.10 * ci
        )

        commitment_probability = float(np.clip(0.18 + 0.70 * organization, 0.05, 0.95))
        confidence = float(np.clip(0.25 + 0.35 * ci + 0.20 * reliability + 0.20 * stability, 0.05, 0.95))

        if commitment_probability >= 0.68:
            lifecycle_state = "commitment"
            expected_lead_hours = 6.0
        elif commitment_probability >= 0.50:
            lifecycle_state = "pre_commitment"
            expected_lead_hours = 12.0
        elif phase > 0.65 and transition > 0.25:
            lifecycle_state = "reconfiguration"
            expected_lead_hours = None
        elif commitment_probability < 0.30:
            lifecycle_state = "decay"
            expected_lead_hours = None
        else:
            lifecycle_state = "quiet"
            expected_lead_hours = None
        
        # --- CI / CSO DERIVED METRICS ---

        persistence = float(np.clip(
            (stability + reliability + ci) / 3.0,
            0.0, 1.0
        ))

        coherence_energy = float(np.clip(
            (0.45 * phase) +
            (0.25 * transition) +
            (0.15 * intensity) +
            (0.15 * ci),
            0.0,
            1.0
        ))

        trajectory_velocity = float(np.clip(
            abs(coherence_energy - persistence),
            0.0, 1.0
        ))

        if "timestamp" in df.columns:
            observed_at = pd.to_datetime(latest["timestamp"], utc=True).isoformat()
        else:
            observed_at = datetime.now(timezone.utc).isoformat()

        out = pd.DataFrame([{
            "observed_at": observed_at,
            "commitment_probability": commitment_probability,
            "expected_lead_hours": expected_lead_hours,
            "event_type_calibrated": lifecycle_state,
            "confidence": confidence,
            "lifecycle_state": lifecycle_state,
            "persistence": persistence,
            "coherence_energy": coherence_energy,
            "trajectory_velocity": trajectory_velocity,
        }])

        out.to_csv(output_csv, index=False)
        return len(out)

    def recalibrate(self, model_version: str) -> str:
        """
        Calls tools/train_weather_commitment_calibrator.py.

        Expected script CLI:
            python tools/train_weather_commitment_calibrator.py --version <id>

        Returns the path to the new calibrator artifact.
        """
        script = self.tools_dir / "train_weather_commitment_calibrator.py"
        if not script.exists():
            raise EngineError(f"Calibrator script not found: {script}")
        cmd = [sys.executable, str(script), "--version", model_version]
        res = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)
        return res.stdout.strip().splitlines()[-1] if res.stdout else ""

    # ---------- Reading outputs ----------

    def load_calibrated_outputs(self, csv_path: Optional[str] = None) -> List[CalibratedRow]:
        """
        Parses tools/weather_commitment_calibrated.csv (or `csv_path` override).
        Expected columns:
            observed_at,commitment_probability,expected_lead_hours,
            event_type_calibrated,confidence,lifecycle_state
        """
        path = Path(csv_path) if csv_path else self.tools_dir / "weather_commitment_calibrated.csv"
        if not path.exists():
            log.warning("engine.calibrated_csv_missing", path=str(path))
            return []

        rows: List[CalibratedRow] = []
        with path.open() as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    rows.append(CalibratedRow(
                        observed_at=_parse_dt(r["observed_at"]),
                        commitment_probability=float(r["commitment_probability"]),
                        expected_lead_hours=_opt_float(r.get("expected_lead_hours")),
                        event_type_calibrated=(r.get("event_type_calibrated") or None),
                        confidence=float(r["confidence"]),
                        lifecycle_state=r.get("lifecycle_state", "quiet"),
                    ))
                except (KeyError, ValueError) as exc:
                    log.warning("engine.calibrated_row_skipped", row=r, error=str(exc))
        return rows

    def load_structural_signatures(self, csv_path: Optional[str] = None) -> List[dict]:
        """
        Parses tools/ci_structural_signatures_app.csv (raw MCC/CI/CSO output).
        Returns plain dicts so callers can inspect arbitrary columns.
        """
        path = Path(csv_path) if csv_path else self.tools_dir / "ci_structural_signatures_app.csv"
        if not path.exists():
            log.warning("engine.signatures_csv_missing", path=str(path))
            return []
        with path.open() as f:
            return list(csv.DictReader(f))

    # ---------- Internal ----------

    @staticmethod
    def _count_csv_rows(path: str) -> int:
        try:
            with open(path) as f:
                return max(0, sum(1 for _ in f) - 1)
        except FileNotFoundError:
            return 0


def _opt_float(v: Optional[str]) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _parse_dt(v: str) -> datetime:
    # Accepts ISO 8601, with or without tz; defaults to UTC.
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
