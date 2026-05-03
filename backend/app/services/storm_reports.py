"""Storm Prediction Center (SPC) Local Storm Reports ingestion.

Fetches daily storm reports from the SPC and writes them to the
ground_truth_events table for use in verification scoring.

Source: https://www.spc.noaa.gov/climo/reports/
URL pattern (per event type, by UTC date):
    YYMMDD_rpts_torn.csv   -- tornadoes
    YYMMDD_rpts_hail.csv   -- hail >= 1 inch (filtered) or all
    YYMMDD_rpts_wind.csv   -- wind reports

Each CSV has a single header row and rows of:
    Time,F_Scale,Location,County,State,Lat,Lon,Comments
where Time is HHMM UTC and severity field name varies by event type
(F_Scale for tornado, Size for hail, Speed for wind).

Note on timing: SPC organizes by "convective day" 12Z-12Z UTC. A
report dated YYMMDD covers from 12Z that day through 12Z the next
day. We treat reports as occurring on their calendar UTC date for
v1; refine later if needed.
"""

import csv
import logging
from datetime import date, datetime, time, timezone
from io import StringIO
from typing import Iterable, List, Optional

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Adjust this import to match your project's model location.
# In Stage 1 you placed GroundTruthEvent in backend/app/db/engine.py,
# so this import follows that path.
from app.db.models.engine import GroundTruthEvent

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPC_BASE_URL = "https://www.spc.noaa.gov/climo/reports"

EVENT_TYPES = ("tornado", "hail", "wind")

URL_SUFFIX = {
    "tornado": "torn",
    "hail": "hail",
    "wind": "wind",
}


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


def fetch_spc_csv(report_date: date, event_type: str, timeout: float = 30.0) -> Optional[str]:
    """Fetch the raw CSV text for one event type and date.

    Returns the CSV text, or None when SPC returns 404 (no reports
    for that date/type — this is a valid empty state, not an error).
    Raises httpx.HTTPError for other transport problems.
    """
    if event_type not in URL_SUFFIX:
        raise ValueError(f"Unknown event_type: {event_type!r}")

    yymmdd = report_date.strftime("%y%m%d")
    suffix = URL_SUFFIX[event_type]
    url = f"{SPC_BASE_URL}/{yymmdd}_rpts_{suffix}.csv"

    log.info("fetching SPC reports", extra={"url": url})
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError as exc:
        log.warning("SPC fetch failed", extra={"url": url, "error": str(exc)})
        raise

    if response.status_code == 404:
        log.info("SPC returned 404 (no reports)", extra={"url": url})
        return None

    response.raise_for_status()
    return response.text


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_spc_csv(text: str, event_type: str, report_date: date) -> List[dict]:
    """Parse SPC CSV text into normalized event dicts.

    Returns a list of dicts ready to insert into ground_truth_events.
    Skips rows that fail validation rather than raising — SPC CSVs
    occasionally contain section headers or partial rows, and we
    prefer to ingest what we can rather than fail the whole batch.
    """
    if not text or not text.strip():
        return []

    reader = csv.DictReader(StringIO(text))
    severity_field = {"tornado": "F_Scale", "hail": "Size", "wind": "Speed"}[event_type]

    events: List[dict] = []
    for row in reader:
        try:
            event = _row_to_event(row, event_type, severity_field, report_date)
        except (ValueError, KeyError, TypeError) as exc:
            log.debug("skipping malformed SPC row", extra={"row": row, "error": str(exc)})
            continue
        if event is not None:
            events.append(event)

    return events


def _row_to_event(
    row: dict,
    event_type: str,
    severity_field: str,
    report_date: date,
) -> Optional[dict]:
    """Convert one SPC CSV row to a normalized event dict, or None to skip."""
    time_str = (row.get("Time") or "").strip()
    if not time_str or time_str.lower() == "time":
        return None  # header row or blank line

    lat_str = (row.get("Lat") or "").strip()
    lon_str = (row.get("Lon") or "").strip()
    if not lat_str or not lon_str:
        return None  # incomplete row

    # SPC times are UTC HHMM (sometimes "0732", sometimes " 732" etc.).
    time_str = time_str.zfill(4)
    if len(time_str) != 4 or not time_str.isdigit():
        return None
    hour = int(time_str[:2])
    minute = int(time_str[2:])
    if hour > 23 or minute > 59:
        return None
    event_at = datetime.combine(report_date, time(hour=hour, minute=minute), tzinfo=timezone.utc)

    lat = float(lat_str)
    lon = float(lon_str)

    severity = (row.get(severity_field) or "").strip() or None

    location = (row.get("Location") or "").strip()
    county = (row.get("County") or "").strip()
    state = (row.get("State") or "").strip()

    # Stable per-row identifier for idempotency. Including coordinates
    # protects against same-time, same-state collisions.
    source_event_id = (
        f"{report_date.isoformat()}|{event_type}|{time_str}|{lat:.4f}|{lon:.4f}|{state}|{location}"
    )

    return {
        "source": "SPC",
        "source_event_id": source_event_id,
        "event_type": event_type,
        "severity": severity,
        "event_at": event_at,
        "latitude": lat,
        "longitude": lon,
        "raw": dict(row),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def upsert_events(db: Session, events: Iterable[dict]) -> dict:
    """Insert events into ground_truth_events idempotently.

    Uses Postgres ON CONFLICT DO NOTHING against the
    (source, source_event_id) unique constraint. Returns counts.
    """
    items = list(events)
    if not items:
        return {"created": 0, "skipped": 0}

    stmt = insert(GroundTruthEvent).values(items)
    stmt = stmt.on_conflict_do_nothing(index_elements=["source", "source_event_id"])
    stmt = stmt.returning(GroundTruthEvent.id)

    result = db.execute(stmt)
    db.commit()

    created = len(result.fetchall())
    skipped = len(items) - created
    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def ingest_for_date(db: Session, report_date: date) -> dict:
    """Fetch + parse + upsert all event types for a single date.

    Returns a per-type summary dict that callers can return to clients
    or log. Failures of individual event types do not abort the others.
    """
    summary: dict = {"date": report_date.isoformat()}

    for event_type in EVENT_TYPES:
        try:
            text = fetch_spc_csv(report_date, event_type)
            if text is None:
                summary[event_type] = {"fetched": 0, "created": 0, "skipped": 0, "note": "no reports"}
                continue

            events = parse_spc_csv(text, event_type, report_date)
            counts = upsert_events(db, events)
            summary[event_type] = {
                "fetched": len(events),
                "created": counts["created"],
                "skipped": counts["skipped"],
            }
        except httpx.HTTPError as exc:
            summary[event_type] = {"error": f"HTTP error: {exc}"}
        except Exception as exc:
            log.exception("ingest_for_date failed", extra={"event_type": event_type})
            summary[event_type] = {"error": str(exc)}

    return summary