import sys; sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.db.models import CalibratedOutput, ModelVersion
from sqlalchemy import select, func
from datetime import datetime, timezone

db = SessionLocal()
n = db.execute(
    select(func.count()).select_from(CalibratedOutput).join(ModelVersion)
    .where(
        ModelVersion.version == 'calibrator-v3.0',
        CalibratedOutput.observed_at >= datetime(2026, 3, 1, tzinfo=timezone.utc),
        CalibratedOutput.observed_at <= datetime(2026, 5, 24, 23, 59, 59, tzinfo=timezone.utc),
    )
).scalar()
print(f'{n:,} calibrator-v3.0 outputs in [2026-03-01, 2026-05-24]')
db.close()