from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.assessment import Assessment as AssessmentModel, ScanJob as ScanJobModel
from app.schemas.scanjob import ScanJob

router = APIRouter(tags=["scan_jobs"])

@router.post("/api/assessments/{assessment_id}/scan-jobs", response_model=ScanJob, status_code=status.HTTP_201_CREATED)
def create_scan_job(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    if not db_assessment.authorization_confirmed:
        raise HTTPException(status_code=403, detail="Cannot create scan job: authorization not confirmed for this assessment")
        
    # Use the assessment's existing scan_profile by default.
    # The scan job is just created as queued. No execution happens here.
    db_scan_job = ScanJobModel(
        assessment_id=assessment_id,
        scan_profile=db_assessment.scan_profile
    )
    db.add(db_scan_job)
    db.commit()
    db.refresh(db_scan_job)
    return db_scan_job

@router.get("/api/assessments/{assessment_id}/scan-jobs", response_model=List[ScanJob])
def get_assessment_scan_jobs(assessment_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    scan_jobs = db.query(ScanJobModel).filter(ScanJobModel.assessment_id == assessment_id).offset(skip).limit(limit).all()
    return scan_jobs

@router.get("/api/scan-jobs/{scan_job_id}", response_model=ScanJob)
def get_scan_job(scan_job_id: int, db: Session = Depends(get_db)):
    db_scan_job = db.query(ScanJobModel).filter(ScanJobModel.id == scan_job_id).first()
    if not db_scan_job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return db_scan_job
