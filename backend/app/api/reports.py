
import hashlib
import secrets
from datetime import datetime, timezone
from app.models.report_share import ReportShareLink
from app.schemas.report import ReportShareLinkCreate, ReportShareLinkResponse
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Response
from app.services.report_export import render_html_report, generate_pdf_report
import re
from sqlalchemy.orm import Session, defer
from typing import List
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportResponse, ReportMetadataResponse, ReportCreateRequest, ReportDataset
from app.services.report_engine import generate_report
import logging

router = APIRouter(tags=["Reports"])
logger = logging.getLogger(__name__)

@router.post("/api/assessments/{assessment_id}/reports", response_model=ReportMetadataResponse)
def create_report(assessment_id: int, req: ReportCreateRequest, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment.authorization_confirmed:
        raise HTTPException(status_code=403, detail="Assessment authorization not confirmed")

    try:
        report = generate_report(db, assessment_id=assessment_id, title=req.title)
        return report
    except Exception as e:
        logger.error(f"Failed to generate report for assessment {assessment_id}: {str(e)}")
        # In a real system we might persist a failed state, but here it's safer to rollback
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal failure during report generation")

@router.get("/api/assessments/{assessment_id}/reports", response_model=List[ReportMetadataResponse])
def list_assessment_reports(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    reports = db.query(Report).filter(Report.assessment_id == assessment_id).options(
        defer(Report.snapshot)
    ).order_by(Report.created_at.desc(), Report.id.asc()).all()

    return reports

@router.get("/api/reports/{report_id}", response_model=ReportMetadataResponse)
def get_report_metadata(report_id: int, assessment_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).options(defer(Report.snapshot)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/api/reports/{report_id}/dataset", response_model=ReportDataset)
def get_report_dataset(report_id: int, assessment_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report snapshot is not available")

    return report.snapshot

@router.get("/api/reports/{report_id}/export/html")
def export_html_report(report_id: int, assessment_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report snapshot is not available")

    html_content = render_html_report(report)

    # Sanitize title for filename
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', report.title.lower())
    filename = f"security-assessment-report-{report.id}-{safe_title}.html"

    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/api/reports/{report_id}/export/pdf")
def export_pdf_report(report_id: int, assessment_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report snapshot is not available")

    pdf_bytes = generate_pdf_report(report)

    # Sanitize title for filename
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', report.title.lower())
    filename = f"security-assessment-report-{report.id}-{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _get_share_status(share: ReportShareLink) -> str:
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if share.revoked_at is not None:
        return "revoked"
    if share.expires_at is not None and now_utc >= share.expires_at:
        return "expired"
    return "active"

@router.post("/api/reports/{report_id}/shares", response_model=ReportShareLinkResponse)
def create_report_share(report_id: int, assessment_id: int, req: ReportShareLinkCreate, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report must be generated before sharing")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # expires_at comes as a timezone-aware UTC datetime from Pydantic, convert to naive UTC for SQLite
    expires_at = req.expires_at.replace(tzinfo=None) if req.expires_at else None

    share_link = ReportShareLink(
        report_id=report_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    # Construct response with raw token just this once
    resp = ReportShareLinkResponse(id=share_link.id, report_id=share_link.report_id, created_at=share_link.created_at, expires_at=share_link.expires_at, revoked_at=share_link.revoked_at, last_accessed_at=share_link.last_accessed_at, access_count=share_link.access_count, status="", share_url="")
    resp.status = _get_share_status(share_link)
    resp.share_url = f"/shared/reports/{raw_token}"
    return resp

@router.get("/api/reports/{report_id}/shares", response_model=List[ReportShareLinkResponse])
def list_report_shares(report_id: int, assessment_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    shares = db.query(ReportShareLink).filter(ReportShareLink.report_id == report_id).order_by(ReportShareLink.created_at.desc()).all()

    results = []
    for share in shares:
        resp = ReportShareLinkResponse(id=share.id, report_id=share.report_id, created_at=share.created_at, expires_at=share.expires_at, revoked_at=share.revoked_at, last_accessed_at=share.last_accessed_at, access_count=share.access_count, status="", share_url=None)
        resp.status = _get_share_status(share)
        results.append(resp)

    return results

@router.post("/api/shares/{share_id}/revoke", response_model=ReportShareLinkResponse)
def revoke_report_share(share_id: int, assessment_id: int, db: Session = Depends(get_db)):
    share = db.query(ReportShareLink).join(Report).filter(ReportShareLink.id == share_id, Report.assessment_id == assessment_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")

    if share.revoked_at is None:
        share.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(share)

    resp = ReportShareLinkResponse(id=share.id, report_id=share.report_id, created_at=share.created_at, expires_at=share.expires_at, revoked_at=share.revoked_at, last_accessed_at=share.last_accessed_at, access_count=share.access_count, status="", share_url=None)
    resp.status = _get_share_status(share)
    return resp

@router.get("/api/shared/reports/{token}", response_model=ReportResponse)
def get_shared_report(token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    share = db.query(ReportShareLink).filter(ReportShareLink.token_hash == token_hash).first()

    if not share:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer available.")

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    if share.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer available.")

    if share.expires_at is not None and now_utc >= share.expires_at:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer available.")

    report = db.query(Report).filter(Report.id == share.report_id).first()
    if not report or report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer available.")

    # Increment access tracking
    share.access_count += 1
    share.last_accessed_at = now_utc
    db.commit()

    return report
