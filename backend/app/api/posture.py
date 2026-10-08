from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.posture import PostureResult
from app.services.posture_engine import calculate_posture

router = APIRouter(tags=["posture"])

@router.get("/api/assessments/{assessment_id}/posture", response_model=PostureResult)
def get_assessment_posture(assessment_id: int, db: Session = Depends(get_db)):
    try:
        result = calculate_posture(db, assessment_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
