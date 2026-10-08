from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.assessment import Assessment as AssessmentModel
from app.schemas.ai_analyst import APIAnalystRequest, AIAnalystResponse, AIAnalystRequest
from app.services.ai_analyst_engine import execute_analysis
from app.services.ai_provider import MockAIProvider

router = APIRouter(tags=["ai_analyst"])

# Mock provider instantiated securely at the module level.
# In a real environment, this would be injected or configured via env vars.
# We NEVER accept provider config from the client request.
_provider = MockAIProvider()

@router.post("/api/assessments/{assessment_id}/ai-analysis", response_model=AIAnalystResponse)
def analyze_assessment(assessment_id: int, request: APIAnalystRequest, db: Session = Depends(get_db)):
    # 1. Verify Assessment Exists
    assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    # 2. Build Internal Service Request (Guarantees isolation of assessment_id)
    service_request = AIAnalystRequest(
        assessment_id=assessment_id,
        analysis_type=request.analysis_type,
        instructions=request.question
    )
    
    # 3. Execute Analysis safely
    try:
        response = execute_analysis(db, service_request, _provider)
        return response
    except ValueError as e:
        # Expected controlled errors (e.g., from context builder)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected internal errors (e.g., provider failure)
        # DO NOT expose raw stack trace
        raise HTTPException(status_code=500, detail="An internal error occurred during analysis.")
