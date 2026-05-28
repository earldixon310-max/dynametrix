"""Check atmospheric_observations date range and split-candidate balance for CT-v1 diagnostic."""
import sys; sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.db.models import Location
from app.db.models.engine import AtmosphericObservation
from sqlalchemy import select, func
from datetime import datetime, timezone

db = SessionLocal()

# Overall date range and total count
result = db.execute(
    select(
        func.min(AtmosphericObservation.observed_at).label('min_at'),
        func.max(AtmosphericObservation.observed_at).label('max_at'),
        func.count().label('total'),
        func.count(func.distinct(AtmosphericObservation.location_id)).label('locations'),
    )
    .select_from(AtmosphericObservation)
).one()
print(f"AtmosphericObservation date range: {result.min_at} -> {result.max_at}")
print(f"AtmosphericObservation total rows: {result.total:,}")
print(f"Distinct locations: {result.locations}\n")

# Candidate training/comparison split balance
# Window is ~April 20 to ~May 29 = ~40 days, so candidates are mid-range dates
print("Candidate training/comparison split balance:")
print(f"  {'Split date':<14} {'train':>10} {'comp':>10} {'ratio':>8}  {'days train':>12} {'days comp':>12}")
for split_date in [
    datetime(2026, 5, 1, tzinfo=timezone.utc),
    datetime(2026, 5, 4, tzinfo=timezone.utc),
    datetime(2026, 5, 7, tzinfo=timezone.utc),
    datetime(2026, 5, 10, tzinfo=timezone.utc),
    datetime(2026, 5, 13, tzinfo=timezone.utc),
    datetime(2026, 5, 15, tzinfo=timezone.utc),
]:
    train_count = db.execute(
        select(func.count())
        .select_from(AtmosphericObservation)
        .where(AtmosphericObservation.observed_at < split_date)
    ).scalar()
    comp_count = db.execute(
        select(func.count())
        .select_from(AtmosphericObservation)
        .where(AtmosphericObservation.observed_at >= split_date)
    ).scalar()
    ratio = (train_count / comp_count) if comp_count > 0 else float('inf')
    train_days = (split_date - result.min_at).days
    comp_days = (result.max_at - split_date).days + 1
    print(f"  {split_date.strftime('%Y-%m-%d'):<14} {train_count:>10,} {comp_count:>10,} {ratio:>8.2f}  {train_days:>12} {comp_days:>12}")

db.close()
