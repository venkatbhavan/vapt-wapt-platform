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
def get_report_metadata(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).options(defer(Report.snapshot)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/api/reports/{report_id}/dataset", response_model=ReportDataset)
def get_report_dataset(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report snapshot is not available")

    return report.snapshot

@router.get("/api/reports/{report_id}/export/html")
def export_html_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
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
def export_pdf_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
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

@router.post("/api/reports/{report_id}/share", response_model=ReportMetadataResponse)
def share_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Report must be generated before sharing")
        
    if not report.share_token:
        report.share_token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(report)
        
    return report

@router.post("/api/reports/{report_id}/unshare", response_model=ReportMetadataResponse)
def unshare_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    report.share_token = None
    db.commit()
    db.refresh(report)
    
    return report

@router.get("/api/shared/reports/{token}", response_model=ReportResponse)
def get_shared_report(token: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.share_token == token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Shared report not found")
        
    if report.status != ReportStatus.generated or not report.snapshot:
        raise HTTPException(status_code=400, detail="Shared report snapshot is not available")
        
    return report
