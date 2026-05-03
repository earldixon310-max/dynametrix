"""Location CRUD (admin/analyst can manage; viewers can read)."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_admin, require_analyst, require_viewer
from app.db.models import Location
from app.db.session import get_db
from app.deps import AuthenticatedUser
from app.schemas.dashboard import LocationOut
from app.schemas.onboarding import LocationInput

router = APIRouter()


def _scope(db: Session, customer_id):
    return db.scalars(select(Location).where(Location.customer_id == customer_id))


@router.get("", response_model=List[LocationOut])
def list_locations(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_viewer()),
):
    return list(_scope(db, current_user.customer_id))


@router.post("", response_model=LocationOut, status_code=201)
def create_location(
    payload: LocationInput,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    loc = Location(
        customer_id=current_user.customer_id,
        label=payload.label, address=payload.address,
        latitude=payload.latitude, longitude=payload.longitude,
        timezone=payload.timezone, is_active=True,
    )
    db.add(loc); db.commit(); db.refresh(loc)
    return loc


@router.delete("/{location_id}", status_code=204)
def delete_location(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    loc = db.get(Location, location_id)
    if not loc or loc.customer_id != current_user.customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    db.delete(loc); db.commit()
    return None
