from fastapi import APIRouter, Depends, HTTPException, status
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
