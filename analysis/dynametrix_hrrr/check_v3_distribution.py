import sys; sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.db.models import CalibratedOutput, ModelVersion
from sqlalchemy import select, func, cast, Date

db = SessionLocal()

# Overall date range and count
result = db.execute(
    select(
        func.min(CalibratedOutput.observed_at).label('min_at'),
        func.max(CalibratedOutput.observed_at).label('max_at'),
        func.count().label('total'),
    )
    .select_from(CalibratedOutput).join(ModelVersion)
    .where(ModelVersion.version == 'calibrator-v3.0')
).one()
print(f"v3 date range: {result.min_at} -> {result.max_at}")
print(f"v3 total rows: {result.total:,}\n")

# Per-day breakdown to see continuity
daily = db.execute(
    select(
        cast(CalibratedOutput.observed_at, Date).label('day'),
        func.count().label('n'),
    )
    .select_from(CalibratedOutput).join(ModelVersion)
    .where(ModelVersion.version == 'calibrator-v3.0')
    .group_by(cast(CalibratedOutput.observed_at, Date))
    .order_by(cast(CalibratedOutput.observed_at, Date))
).all()
print(f"Per-day count ({len(daily)} days with data):")
for row in daily:
    print(f"  {row.day}: {row.n:,}")
db.close()