"""
Report generation: PDF (ReportLab) and CSV.

Reports are written to settings.REPORTS_LOCAL_DIR (or pushed to S3 if AWS is
configured). The Report row stores the path; downloads stream the file from
that location.
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    CalibratedOutput, Customer, Location, Report, ReportFormat,
    StructuralEvent, ModelVersion,
)
from app.utils.copy import (
    DISCLAIMER_LONG, lifecycle_label, event_label, time_to_impact, recommended_action,
)

settings = get_settings()

PRIMARY_HEX = "#3459bc"
PRIMARY = colors.HexColor(PRIMARY_HEX)


def _ensure_reports_dir() -> Path:
    p = Path(settings.REPORTS_LOCAL_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _file_path(customer_id: uuid.UUID, fmt: ReportFormat) -> Path:
    d = _ensure_reports_dir() / str(customer_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"report-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.{fmt.value}"


def _load_data(
    db: Session,
    *,
    customer_id: uuid.UUID,
    location_id: Optional[uuid.UUID],
    period_start: Optional[datetime],
    period_end: Optional[datetime],
) -> Tuple[Customer, Optional[Location], List[CalibratedOutput], List[StructuralEvent], Optional[ModelVersion]]:
    customer = db.get(Customer, customer_id)
    location = db.get(Location, location_id) if location_id else None

    co_q = select(CalibratedOutput).where(CalibratedOutput.customer_id == customer_id)
    se_q = select(StructuralEvent).where(StructuralEvent.customer_id == customer_id)

    if location_id:
        co_q = co_q.where(CalibratedOutput.location_id == location_id)
        se_q = se_q.where(StructuralEvent.location_id == location_id)
    if period_start:
        co_q = co_q.where(CalibratedOutput.observed_at >= period_start)
        se_q = se_q.where(StructuralEvent.observed_at >= period_start)
    if period_end:
        co_q = co_q.where(CalibratedOutput.observed_at <= period_end)
        se_q = se_q.where(StructuralEvent.observed_at <= period_end)

    co_q = co_q.order_by(CalibratedOutput.observed_at.desc()).limit(500)
    se_q = se_q.order_by(StructuralEvent.observed_at.desc()).limit(500)

    calibrated = list(db.scalars(co_q))
    events = list(db.scalars(se_q))
    mv = db.scalar(select(ModelVersion).where(ModelVersion.is_default.is_(True)))
    return customer, location, calibrated, events, mv


# ---------- CSV ----------

def generate_csv(
    db: Session, *,
    customer_id: uuid.UUID,
    requested_by_user_id: Optional[uuid.UUID],
    location_id: Optional[uuid.UUID] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Report:
    customer, location, calibrated, _events, mv = _load_data(
        db, customer_id=customer_id, location_id=location_id,
        period_start=period_start, period_end=period_end,
    )
    path = _file_path(customer_id, ReportFormat.CSV)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "observed_at", "location", "lifecycle_state", "event_type",
            "commitment_probability", "expected_lead_hours", "confidence",
            "model_version",
        ])
        for c in calibrated:
            w.writerow([
                c.observed_at.isoformat(),
                location.label if location else "",
                c.lifecycle_state.value if hasattr(c.lifecycle_state, "value") else c.lifecycle_state,
                (c.event_type_calibrated.value if c.event_type_calibrated else ""),
                f"{c.commitment_probability:.4f}",
                "" if c.expected_lead_hours is None else f"{c.expected_lead_hours:.2f}",
                f"{c.confidence:.4f}",
                (mv.version if mv else ""),
            ])

    report = Report(
        customer_id=customer_id,
        location_id=location_id,
        requested_by_user_id=requested_by_user_id,
        format=ReportFormat.CSV,
        file_path=str(path),
        file_size_bytes=path.stat().st_size,
        model_version=(mv.version if mv else None),
        generated_at=datetime.now(timezone.utc),
        period_start=period_start,
        period_end=period_end,
    )
    db.add(report)
    db.flush()
    return report


# ---------- PDF ----------

def generate_pdf(
    db: Session, *,
    customer_id: uuid.UUID,
    requested_by_user_id: Optional[uuid.UUID],
    location_id: Optional[uuid.UUID] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Report:
    customer, location, calibrated, events, mv = _load_data(
        db, customer_id=customer_id, location_id=location_id,
        period_start=period_start, period_end=period_end,
    )
    path = _file_path(customer_id, ReportFormat.PDF)
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, title="Dynametrix Report",
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=PRIMARY, fontSize=22, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=PRIMARY, fontSize=14, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.grey)

    elems = []
    elems.append(Paragraph("Dynametrix", h1))
    elems.append(Paragraph("Structural Intelligence for Dynamic Systems", body))
    elems.append(Spacer(1, 12))

    meta_rows = [
        ["Customer", customer.company_name if customer else ""],
        ["Location", location.label if location else "All locations"],
        ["Period", f"{period_start or '—'} → {period_end or '—'}"],
        ["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
        ["Model version", mv.version if mv else "—"],
    ]
    t = Table(meta_rows, colWidths=[1.4 * inch, 5.0 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), PRIMARY),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6fb")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde2ec")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde2ec")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(t)

    # ---- Current state ----
    elems.append(Paragraph("Current structural state", h2))
    if calibrated:
        latest = calibrated[0]
        latest_et = latest.event_type_calibrated.value if latest.event_type_calibrated else "—"
        rows = [
            ["Lifecycle state", lifecycle_label(latest.lifecycle_state.value if hasattr(latest.lifecycle_state, 'value') else latest.lifecycle_state)],
            ["Event type", event_label(latest_et)],
            ["Commitment probability", f"{latest.commitment_probability:.0%}"],
            ["Confidence level", f"{latest.confidence:.0%}"],
            ["Lead time", time_to_impact(latest.expected_lead_hours)],
            ["Recommended posture", recommended_action(latest_et, latest.confidence)],
        ]
        st = Table(rows, colWidths=[1.8 * inch, 4.6 * inch])
        st.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TEXTCOLOR", (0, 0), (0, -1), PRIMARY),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6fb")),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde2ec")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde2ec")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elems.append(st)
    else:
        elems.append(Paragraph("No calibrated outputs in this period.", body))

    # ---- Timeline ----
    elems.append(Paragraph("Timeline of detected structural states", h2))
    if events:
        data = [["Observed (UTC)", "Lifecycle", "Event"]]
        for ev in events[:25]:
            data.append([
                ev.observed_at.strftime("%Y-%m-%d %H:%M"),
                lifecycle_label(ev.lifecycle_state.value if hasattr(ev.lifecycle_state, 'value') else ev.lifecycle_state),
                event_label(ev.event_type.value) if ev.event_type else "—",
            ])
        tbl = Table(data, colWidths=[1.6 * inch, 2.6 * inch, 2.2 * inch], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9ff")]),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde2ec")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dde2ec")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elems.append(tbl)
    else:
        elems.append(Paragraph("No structural events recorded in this period.", body))

    # ---- Confidence / disclaimers ----
    elems.append(Spacer(1, 14))
    elems.append(Paragraph("Confidence explanation", h2))
    elems.append(Paragraph(
        "Confidence is a calibrated reliability score (0–1) derived from agreement among "
        "MCC, CI, and CSO structural metrics with the calibrator's training distribution. "
        "It is not a probability of impact — it reflects the strength of the structural signature.",
        body,
    ))

    elems.append(PageBreak())
    elems.append(Paragraph("Disclaimer", h2))
    elems.append(Paragraph(DISCLAIMER_LONG, body))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(
        f"Generated by Dynametrix · model version: {mv.version if mv else '—'}",
        small,
    ))

    doc.build(elems)

    report = Report(
        customer_id=customer_id,
        location_id=location_id,
        requested_by_user_id=requested_by_user_id,
        format=ReportFormat.PDF,
        file_path=str(path),
        file_size_bytes=path.stat().st_size,
        model_version=(mv.version if mv else None),
        generated_at=datetime.now(timezone.utc),
        period_start=period_start,
        period_end=period_end,
    )
    db.add(report)
    db.flush()
    return report
