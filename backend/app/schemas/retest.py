from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.finding import Evidence
from app.models.retest import RetestStatus, RetestResultStatus, RetestConfidence

class RetestResultBase(BaseModel):
    result: RetestResultStatus
    confidence: RetestConfidence
    rationale: str
    previous_finding_id: int
    current_finding_id: Optional[int] = None

class RetestResultCreate(RetestResultBase):
    retest_request_id: int

class RetestResultResponse(RetestResultBase):
    id: int
    retest_request_id: int
    created_at: datetime
    updated_at: datetime
    evidence: list[Evidence] = Field(default_factory=list)

    class Config:
        orm_mode = True


class RetestRequestBase(BaseModel):
    finding_id: int
    status: RetestStatus = RetestStatus.requested

class RetestRequestCreate(RetestRequestBase):
    pass

class RetestRequestResponse(RetestRequestBase):
    id: int
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    result: Optional[RetestResultResponse] = None

    class Config:
        orm_mode = True
