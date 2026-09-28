from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.assessment import Assessment as AssessmentModel, Project as ProjectModel
from app.schemas.assessment import Assessment, AssessmentCreate

router = APIRouter(tags=["assessments"])

@router.post("/api/projects/{project_id}/assessments", response_model=Assessment, status_code=status.HTTP_201_CREATED)
def create_assessment(project_id: int, assessment: AssessmentCreate, db: Session = Depends(get_db)):
    # Verify that the referenced project exists
    db_project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not assessment.authorization_confirmed:
        raise HTTPException(status_code=400, detail="Authorization must be explicitly confirmed")

    db_assessment = AssessmentModel(
        project_id=project_id,
        name=assessment.name,
        target=assessment.target,
        authorization_confirmed=assessment.authorization_confirmed,
        scope=assessment.scope,
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment

@router.get("/api/projects/{project_id}/assessments", response_model=List[Assessment])
def get_project_assessments(project_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    assessments = db.query(AssessmentModel).filter(AssessmentModel.project_id == project_id).offset(skip).limit(limit).all()
    return assessments

@router.get("/api/assessments/{assessment_id}", response_model=Assessment)
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return db_assessment

from app.schemas.summary import AssessmentSummary, SeverityCounts, RiskCounts, StatusCounts, ScanJobCounts
from app.models.assessment import ScanJob as ScanJobModel, Finding as FindingModel

@router.get("/api/assessments/{assessment_id}/summary", response_model=AssessmentSummary)
def get_assessment_summary(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    scan_jobs = db.query(ScanJobModel).filter(ScanJobModel.assessment_id == assessment_id).all()
    
    sj_counts = ScanJobCounts()
    for sj in scan_jobs:
        status_val = sj.status.value if hasattr(sj.status, 'value') else sj.status
        if hasattr(sj_counts, status_val):
            setattr(sj_counts, status_val, getattr(sj_counts, status_val) + 1)
            
    findings = db.query(FindingModel).join(ScanJobModel).filter(ScanJobModel.assessment_id == assessment_id).all()
    
    total_findings = len(findings)
    sev_counts = SeverityCounts()
    risk_counts = RiskCounts()
    stat_counts = StatusCounts()
    
    for f in findings:
        sev_val = f.severity.value if hasattr(f.severity, 'value') else f.severity
        if hasattr(sev_counts, sev_val):
            setattr(sev_counts, sev_val, getattr(sev_counts, sev_val) + 1)
            
        if f.risk_level:
            risk_val = f.risk_level.value if hasattr(f.risk_level, 'value') else f.risk_level
            if hasattr(risk_counts, risk_val):
                setattr(risk_counts, risk_val, getattr(risk_counts, risk_val) + 1)
                
        stat_val = f.status.value if hasattr(f.status, 'value') else f.status
        if hasattr(stat_counts, stat_val):
            setattr(stat_counts, stat_val, getattr(stat_counts, stat_val) + 1)
            
    return AssessmentSummary(
        assessment_id=assessment_id,
        total_findings=total_findings,
        severity_counts=sev_counts,
        risk_counts=risk_counts,
        status_counts=stat_counts,
        scan_job_counts=sj_counts
    )
