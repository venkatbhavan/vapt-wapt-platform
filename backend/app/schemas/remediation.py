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

# Phase 9C API Response Schemas

class RemediationMappingFinding(BaseModel):
    id: int
    title: str
    severity: str
    status: str
    normalized_type: Optional[str] = None

    class Config:
        from_attributes = True

class RemediationMappingDetail(BaseModel):
    id: int
    finding: RemediationMappingFinding
    mapping_confidence: str
    rationale: str

    class Config:
        from_attributes = True

class RemediationGuidanceWithMappings(BaseModel):
    id: int
    title: str
    summary: str
    detailed_guidance: str
    remediation_type: str
    priority: str
    verification_guidance: str
    mappings: List[RemediationMappingDetail]

    class Config:
        from_attributes = True

class AssessmentRemediationResponse(BaseModel):
    assessment_id: int
    remediations: List[RemediationGuidanceWithMappings]

    class Config:
        from_attributes = True
