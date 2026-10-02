from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.assessment import Finding, ScanJob, Assessment
from app.models.retest import RetestRequest
from app.schemas.retest import RetestRequestResponse
from app.services.retest_engine import run_retest

router = APIRouter(tags=["Retests"])

@router.post("/api/findings/{finding_id}/retests", response_model=RetestRequestResponse)
def create_retest(finding_id: int, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    scan_job = finding.scan_job
    if not scan_job or not scan_job.assessment:
        raise HTTPException(status_code=400, detail="Finding is missing valid assessment context")
        
    if not scan_job.assessment.authorization_confirmed:
        raise HTTPException(status_code=403, detail="Assessment authorization not confirmed")

    retest_req = RetestRequest(finding_id=finding.id)
    db.add(retest_req)
    db.commit()
    db.refresh(retest_req)
    
    try:
        updated_req = run_retest(db, retest_req.id)
        db.refresh(updated_req)
        return updated_req
    except Exception as e:
        # Unexpected internal failure in the API layer catching (run_retest itself should handle internals)
        raise HTTPException(status_code=500, detail="Internal Retest Engine failure")

@router.get("/api/findings/{finding_id}/retests", response_model=List[RetestRequestResponse])
def get_finding_retests(finding_id: int, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    retests = db.query(RetestRequest).filter(
        RetestRequest.finding_id == finding_id
    ).order_by(RetestRequest.requested_at.desc()).all()
    
    return retests

@router.get("/api/retests/{retest_request_id}", response_model=RetestRequestResponse)
def get_retest(retest_request_id: int, db: Session = Depends(get_db)):
    retest = db.query(RetestRequest).filter(RetestRequest.id == retest_request_id).first()
    if not retest:
        raise HTTPException(status_code=404, detail="Retest request not found")
    return retest

@router.get("/api/assessments/{assessment_id}/retests", response_model=List[RetestRequestResponse])
def get_assessment_retests(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    retests = db.query(RetestRequest).join(Finding).join(ScanJob).filter(
        ScanJob.assessment_id == assessment_id
    ).order_by(RetestRequest.requested_at.desc()).all()
    
    return retests
