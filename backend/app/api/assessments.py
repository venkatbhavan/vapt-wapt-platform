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
