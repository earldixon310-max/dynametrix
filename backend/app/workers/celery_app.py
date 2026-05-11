"""Celery app instance. Run worker with: celery -A app.workers.celery_app worker -l info"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "dynametrix",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="dynametrix.default",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# ---------------------------------------------------------------------------
# Celery Beat schedule
#
# Runs scheduled background tasks. The beat process must be enabled —
# in dev we use the embedded -B flag on the worker (see docker-compose.yml).
# For multi-worker production deployments, run `celery beat` as its own
# service and remove -B from the worker command.
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "ingest-atmospheric-hourly": {
        "task": "dynametrix.atmospheric.ingest_all_locations",
        "schedule": crontab(minute=0),
        "options": {"queue": "dynametrix.default"},
    },
    "ingest-storm-reports-daily": {
        "task": "dynametrix.verification.ingest_storm_reports_daily",
        "schedule": crontab(hour=14, minute=0),
        "options": {"queue": "dynametrix.default"},
    },
    "run-pipeline-hourly": {
        "task": "dynametrix.pipeline.run_all_locations",
        "schedule": crontab(minute=5),
        "options": {"queue": "dynametrix.default"},
    },
    "backfill-verification-daily": {
        "task": "dynametrix.verification.backfill_outcomes_daily",
        "schedule": crontab(hour=14, minute=30),
        "options": {"queue": "dynametrix.default"},
    },
}