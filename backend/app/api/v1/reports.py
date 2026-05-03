"""Report generation + download endpoints."""
import os
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_analyst, require_viewer
from app.db.models import AuditAction, Report, ReportFormat
from app.db.session import get_db
from app.deps import AuthenticatedUser
from app.schemas.reports import ReportOut, ReportRequest
from app.services import audit
from app.services.report_service import generate_csv, generate_pdf

router = APIRouter()


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_analyst()),
):
    if payload.format == "pdf":
        report = generate_pdf(
            db, customer_id=current_user.customer_id,
            requested_by_user_id=current_user.id, location_id=payload.location_id,
            period_start=payload.period_start, period_end=payload.period_end,
        )
    else:
        report = generate_csv(
            db, customer_id=current_user.customer_id,
            requested_by_user_id=current_user.id, location_id=payload.location_id,
            period_start=payload.period_start, period_end=payload.period_end,
        )

    audit.record(
        db, action=AuditAction.REPORT_GENERATED,
        customer_id=current_user.customer_id, user_id=current_user.id,
        location_id=payload.location_id, model_version=report.model_version,
        context={"format": report.format.value, "report_id": str(report.id)},
    )
    db.commit()
    return ReportOut(
        id=report.id, format=report.format.value, file_size_bytes=report.file_size_bytes,
        model_version=report.model_version, generated_at=report.generated_at,
        period_start=report.period_start, period_end=report.period_end,
    )


@router.get("", response_model=List[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_viewer()),
):
    rows = list(db.scalars(
        select(Report).where(Report.customer_id == current_user.customer_id)
        .order_by(Report.generated_at.desc())
    ))
    return [
        ReportOut(
            id=r.id, format=r.format.value, file_size_bytes=r.file_size_bytes,
            model_version=r.model_version, generated_at=r.generated_at,
            period_start=r.period_start, period_end=r.period_end,
        )
        for r in rows
    ]


@router.get("/{report_id}/download")
def download_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_viewer()),
):
    r = db.get(Report, report_id)
    if not r or r.customer_id != current_user.customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if not os.path.exists(r.file_path):
        raise HTTPException(status.HTTP_410_GONE, "Report file no longer available")

    audit.record(
        db, action=AuditAction.REPORT_DOWNLOADED,
        customer_id=current_user.customer_id, user_id=current_user.id,
        location_id=r.location_id, model_version=r.model_version,
        context={"report_id": str(r.id)},
    )
    db.commit()

    media = "application/pdf" if r.format == ReportFormat.PDF else "text/csv"
    filename = os.path.basename(r.file_path)
    return FileResponse(r.file_path, media_type=media, filename=filename)
