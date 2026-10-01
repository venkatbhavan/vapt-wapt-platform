from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.compliance import MappingConfidence, MappingType

class ComplianceControlBase(BaseModel):
    control_id: str
    title: str
    description: Optional[str] = None

class ComplianceControlRead(ComplianceControlBase):
    id: int
    framework_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ComplianceFrameworkBase(BaseModel):
    name: str
    version: str
    description: Optional[str] = None

class ComplianceFrameworkRead(ComplianceFrameworkBase):
    id: int
    created_at: datetime
    updated_at: datetime
    controls: List[ComplianceControlRead] = []
    model_config = ConfigDict(from_attributes=True)

class FindingComplianceMappingBase(BaseModel):
    rationale: str
    mapping_type: MappingType
    mapping_confidence: MappingConfidence
    source: str

class FindingComplianceMappingRead(FindingComplianceMappingBase):
    id: int
    finding_id: int
    control_id: int
    created_at: datetime
    updated_at: datetime
    control: ComplianceControlRead
    model_config = ConfigDict(from_attributes=True)

# Phase 8C API Response Schemas

class ComplianceMappingResponse(BaseModel):
    id: int
    finding_id: int
    finding_title: str
    finding_severity: str
    finding_status: str
    mapping_type: str
    mapping_confidence: str
    rationale: str
    source: str
    model_config = ConfigDict(from_attributes=True)

class ComplianceControlResponse(BaseModel):
    id: int
    control_id: str
    title: str
    description: Optional[str] = None
    mappings: List[ComplianceMappingResponse]
    model_config = ConfigDict(from_attributes=True)

class ComplianceFrameworkResponse(BaseModel):
    id: int
    name: str
    version: str
    description: Optional[str] = None
    controls: List[ComplianceControlResponse]
    model_config = ConfigDict(from_attributes=True)

class ComplianceAssessmentResponse(BaseModel):
    assessment_id: int
    frameworks: List[ComplianceFrameworkResponse]
    model_config = ConfigDict(from_attributes=True)
