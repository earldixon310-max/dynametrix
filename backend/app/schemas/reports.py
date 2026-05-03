"""Report schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ReportRequest(BaseModel):
    format: str = Field(pattern=r"^(pdf|csv)$")
    location_id: Optional[UUID] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ReportOut(ORMModel):
    id: UUID
    format: str
    file_size_bytes: Optional[int]
    model_version: Optional[str]
    generated_at: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]

    model_config = {
        "protected_namespaces": ()
    }
