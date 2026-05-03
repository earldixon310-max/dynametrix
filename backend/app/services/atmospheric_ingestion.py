"""Open-Meteo atmospheric observation ingestion.

Fetches hourly atmospheric data — CAPE, lifted index, multi-level
temperature and wind, surface state, etc. — for each monitored
location and persists into the atmospheric_observations table.

These observations are the raw inputs the pipeline calibrator will
eventually consume to make commitment probability responsive to actual
atmospheric reality rather than internal calibrator dynamics.

Source: Open-Meteo (https://open-meteo.com).
- Free, no API key required.
- Returns hourly JSON.
- Default model: gfs_seamless (combines GFS Global with HRRR where
  available; HRRR is the operational US severe-weather model).
- Variables not available from the chosen model come back as null and
  are stored as NULL in the database.

Idempotent: (location_id, observed_at, source) unique constraint
ensures re-fetching the same hour for the same location updates
nothing. Re-runs are safe.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Location
from app.db.models.engine import AtmosphericObservation

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "open-meteo"

# Hourly variables we request from Open-Meteo. Variables that aren't
# available from the chosen model will return null and end up as NULL
# in the database. The schema columns are nullable for this reason.
HOURLY_VARIABLES = [
    "temperature_2m",
    "dew_point_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_speed_80m",
    "wind_direction_80m",
    "cape",
]


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


def fetch_open_meteo(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: Optional[date] = None,
    timeout: float = 30.0,
) -> Optional[dict]:
    """Fetch hourly atmospheric data from Open-Meteo for a date range."""
    if end_date is None:
        end_date = start_date

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
        "wind_speed_unit": "ms",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "models": "gfs_seamless",
    }

    log.info(
        "fetching Open-Meteo data",
        extra={
            "lat": latitude,
            "lon": longitude,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    )

    response = httpx.get(OPEN_METEO_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _safe_get(hourly: dict, key: str, idx: int) -> Optional[float]:
    """Pull a numeric value from an hourly array, returning None on
    missing key, out-of-range index, null value, or non-numeric value."""
    arr = hourly.get(key)
    if arr is None or idx >= len(arr):
        return None
    val = arr[idx]
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_open_meteo(payload: dict, location_id: UUID) -> List[dict]:
    """Convert an Open-Meteo response into observation dicts.

    Returns a list ready for insertion into atmospheric_observations.
    Skips rows where observed_at can't be parsed.
    """
    if not payload or "hourly" not in payload:
        return []

    hourly = payload["hourly"]
    times = hourly.get("time", [])
    if not times:
        return []

    observations: List[dict] = []
    for i, time_str in enumerate(times):
        try:
            observed_at = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        obs = {
            "location_id": location_id,
            "source": SOURCE,
            "observed_at": observed_at,
            "cape": _safe_get(hourly, "cape", i),
            "lifted_index": _safe_get(hourly, "lifted_index", i),
            "convective_inhibition": _safe_get(hourly, "convective_inhibition", i),
            "temperature_2m": _safe_get(hourly, "temperature_2m", i),
            "dewpoint_2m": _safe_get(hourly, "dew_point_2m", i),
            "relative_humidity_2m": _safe_get(hourly, "relative_humidity_2m", i),
            "pressure_msl": _safe_get(hourly, "pressure_msl", i),
            "precipitation": _safe_get(hourly, "precipitation", i),
            "wind_speed_10m": _safe_get(hourly, "wind_speed_10m", i),
            "wind_direction_10m": _safe_get(hourly, "wind_direction_10m", i),
            "wind_speed_80m": _safe_get(hourly, "wind_speed_80m", i),
            "wind_direction_80m": _safe_get(hourly, "wind_direction_80m", i),
            "wind_speed_180m": _safe_get(hourly, "wind_speed_180m", i),
            "wind_direction_180m": _safe_get(hourly, "wind_direction_180m", i),
            "temperature_500hPa": _safe_get(hourly, "temperature_500hPa", i),
            "temperature_700hPa": _safe_get(hourly, "temperature_700hPa", i),
            "temperature_850hPa": _safe_get(hourly, "temperature_850hPa", i),
            "precipitable_water": _safe_get(hourly, "precipitable_water", i),
            "raw": {
                k: (hourly[k][i] if i < len(hourly[k]) else None)
                for k in hourly.keys()
                if k != "time" and isinstance(hourly[k], list)
            },
        }
        observations.append(obs)

    return observations


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def upsert_observations(db: Session, observations: List[dict]) -> dict:
    """Idempotent upsert into atmospheric_observations.

    Uses ON CONFLICT DO NOTHING against (location_id, observed_at, source).
    Returns counts of new vs already-present rows.
    """
    items = list(observations)
    if not items:
        return {"created": 0, "skipped": 0}

    stmt = insert(AtmosphericObservation).values(items)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["location_id", "observed_at", "source"]
    )
    stmt = stmt.returning(AtmosphericObservation.id)

    result = db.execute(stmt)
    db.commit()

    created = len(result.fetchall())
    skipped = len(items) - created
    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# Orchestrators
# ---------------------------------------------------------------------------


def ingest_for_location(
    db: Session,
    location: Location,
    past_days: int = 2,
    forecast_days: int = 1,
) -> dict:
    """Fetch and store atmospheric data for one location.

    Default window: last 2 days (for verification matching) plus the
    next 1 day (for future pipeline use). Tune as needed.
    """
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=past_days)
    end_date = today + timedelta(days=forecast_days)

    try:
        payload = fetch_open_meteo(
            latitude=location.latitude,
            longitude=location.longitude,
            start_date=start_date,
            end_date=end_date,
        )
    except httpx.HTTPError as exc:
        log.warning(
            "atmospheric fetch failed",
            extra={"location_id": str(location.id), "error": str(exc)},
        )
        return {
            "location_id": str(location.id),
            "label": location.label,
            "error": f"HTTP error: {exc}",
        }

    if not payload:
        return {
            "location_id": str(location.id),
            "label": location.label,
            "error": "empty response",
        }

    observations = parse_open_meteo(payload, location.id)
    counts = upsert_observations(db, observations)

    return {
        "location_id": str(location.id),
        "label": location.label,
        "fetched": len(observations),
        "created": counts["created"],
        "skipped": counts["skipped"],
    }


def ingest_for_all_locations(
    db: Session,
    past_days: int = 2,
    forecast_days: int = 1,
) -> List[dict]:
    """Ingest atmospheric data for every location in the database.

    Continues across failures — one location's error doesn't abort
    the others. Returns per-location summaries.
    """
    locations = list(db.scalars(select(Location)))
    summaries: List[dict] = []

    for loc in locations:
        try:
            summary = ingest_for_location(db, loc, past_days, forecast_days)
            summaries.append(summary)
        except Exception as exc:
            log.exception(
                "atmospheric ingestion failed",
                extra={"location_id": str(loc.id), "label": loc.label},
            )
            summaries.append(
                {
                    "location_id": str(loc.id),
                    "label": loc.label,
                    "error": str(exc),
                }
            )
    return summaries