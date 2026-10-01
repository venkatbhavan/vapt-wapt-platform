from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.remediation import RemediationType, RemediationPriority, RemediationMappingConfidence

class RemediationGuidanceBase(BaseModel):
    title: str
    summary: str
    detailed_guidance: str
    remediation_type: RemediationType
    priority: RemediationPriority
    verification_guidance: str

class RemediationGuidanceCreate(RemediationGuidanceBase):
    pass

class RemediationGuidanceResponse(RemediationGuidanceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FindingRemediationBase(BaseModel):
    finding_id: int
    remediation_guidance_id: int
    rationale: str
    mapping_confidence: RemediationMappingConfidence

class FindingRemediationCreate(FindingRemediationBase):
    pass

class FindingRemediationResponse(FindingRemediationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
