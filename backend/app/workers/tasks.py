"""
Background tasks: pipeline runs + alert dispatch.

`run_pipeline_task` is callable both as a Celery task (production) and as a
plain function (FastAPI BackgroundTasks for dev). Keep it sync.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    AuditAction, CalibratedOutput, Customer, Location,
    ModelVersion, PipelineRun, PipelineRunStatus,
)
from app.db.models.engine import EventType, LifecycleState
from app.db.session import SessionLocal
from app.services import alert_service, audit
from app.services.engine_service import CalibratedRow, EngineError, EngineService
from app.utils.copy import recommended_action
from app.workers.celery_app import celery_app

settings = get_settings()
log = get_logger(__name__)

ENGINE = EngineService()


def _persist_calibrated(db, *, customer_id: uuid.UUID, location: Location,
                        model_version: ModelVersion, run: PipelineRun,
                        rows: list[CalibratedRow]) -> list[CalibratedOutput]:
    inserted: list[CalibratedOutput] = []
    for r in rows:
        et = None
        try:
            et = EventType(r.event_type_calibrated) if r.event_type_calibrated else None
        except ValueError:
            log.warning("engine.unknown_event_type", value=r.event_type_calibrated)
        try:
            ls = LifecycleState(r.lifecycle_state)
        except ValueError:
            ls = LifecycleState.QUIET

        co = CalibratedOutput(
            customer_id=customer_id, location_id=location.id,
            model_version_id=model_version.id, pipeline_run_id=run.id,
            observed_at=r.observed_at,
            commitment_probability=r.commitment_probability,
            expected_lead_hours=r.expected_lead_hours,
            event_type_calibrated=et, confidence=r.confidence,
            lifecycle_state=ls,
            recommended_action=recommended_action(et.value if et else "", r.confidence),
        )
        db.add(co)
        inserted.append(co)
    db.flush()
    return inserted


@celery_app.task(name="dynametrix.pipeline.run")
def run_pipeline_task(customer_id: str, location_id: str, triggered_by_user_id: Optional[str]) -> dict:
    """
    1. Run the engine pipeline for the location.
    2. Parse calibrated CSV.
    3. Persist CalibratedOutput rows.
    4. Evaluate latest output for alerts and dispatch.
    """
    db = SessionLocal()
    try:
        cust_uuid = uuid.UUID(customer_id)
        loc_uuid = uuid.UUID(location_id)
        triggered_uuid = uuid.UUID(triggered_by_user_id) if triggered_by_user_id else None

        location = db.get(Location, loc_uuid)
        if not location or location.customer_id != cust_uuid:
            return {"ok": False, "reason": "location_not_found"}

        mv = db.scalar(select(ModelVersion).where(ModelVersion.is_default.is_(True)))
        if not mv:
            return {"ok": False, "reason": "no_default_model_version"}

        run = PipelineRun(
            customer_id=cust_uuid, location_id=loc_uuid,
            triggered_by_user_id=triggered_uuid, model_version_id=mv.id,
            status=PipelineRunStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        db.add(run); db.flush()

        out_path = Path(settings.REPORTS_LOCAL_DIR) / "pipeline" / f"{run.id}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            rows_written = ENGINE.run_pipeline(
                db=db, location_id=location.id, output_csv=str(out_path),
            )
            run.rows_processed = rows_written
            run.output_csv_path = str(out_path)

            # Calibrated output is what's actually shown to users.
            calibrated_rows = ENGINE.load_calibrated_outputs(str(out_path))
            inserted = _persist_calibrated(
                db, customer_id=cust_uuid, location=location,
                model_version=mv, run=run, rows=calibrated_rows,
            )

            run.status = PipelineRunStatus.SUCCEEDED
            run.finished_at = datetime.now(timezone.utc)

            audit.record(
                db, action=AuditAction.PIPELINE_RUN,
                customer_id=cust_uuid, user_id=triggered_uuid, location_id=loc_uuid,
                model_version=mv.version,
                context={"run_id": str(run.id), "rows": rows_written, "calibrated_count": len(inserted)},
            )

            # Evaluate latest calibrated point for alerting
            if inserted:
                latest = max(inserted, key=lambda c: c.observed_at)
                alerts = alert_service.evaluate_and_dispatch(
                    db, customer_id=cust_uuid, location=location, calibrated=latest,
                )
                for a in alerts:
                    if a.delivery_status.value == "sent":
                        audit.record(
                            db, action=AuditAction.ALERT_SENT,
                            customer_id=cust_uuid, location_id=loc_uuid,
                            context={"channel": a.channel.value, "event": a.event_type.value,
                                     "confidence": a.confidence},
                        )
            db.commit()
            return {"ok": True, "run_id": str(run.id), "rows": rows_written}

        except EngineError as exc:
            run.status = PipelineRunStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(exc)[:2000]
            db.commit()
            log.error("pipeline.failed", run_id=str(run.id), error=str(exc))
            return {"ok": False, "run_id": str(run.id), "error": str(exc)}
    finally:
        db.close()

@celery_app.task(name="dynametrix.verification.ingest_storm_reports_daily")
def ingest_storm_reports_daily_task(lookback_days: int = 3) -> dict:
    """Daily ingestion of SPC storm reports for verification ground truth.

    Re-ingests the last `lookback_days` calendar days each run (default 3).
    The look-back window catches reports that SPC publishes late as
    spotters and EM personnel file them after the event.

    Idempotent: the (source, source_event_id) unique constraint on
    ground_truth_events ensures duplicate inserts are skipped silently.

    Triggered daily by Celery Beat at 14:00 UTC, after SPC's overnight
    reports have had time to finalize for the prior convective day.
    """
    from app.services.storm_reports import ingest_for_date

    today_utc = datetime.now(timezone.utc).date()
    summaries: list[dict] = []

    db = SessionLocal()
    try:
        for offset in range(1, lookback_days + 1):
            target = today_utc - timedelta(days=offset)
            try:
                summary = ingest_for_date(db, target)
                summaries.append(summary)
                log.info(
                    "verification.storm_reports.ingested",
                    date=target.isoformat(),
                    summary=summary,
                )
            except Exception as exc:
                log.exception(
                    "verification.storm_reports.failed",
                    date=target.isoformat(),
                )
                summaries.append({"date": target.isoformat(), "error": str(exc)})
    finally:
        db.close()

    return {"ok": True, "summaries": summaries}
