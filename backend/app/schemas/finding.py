from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.assessment import FindingSeverity, FindingConfidence, FindingStatus, EvidenceType
from app.risk.models import RiskLevel

class EvidenceBase(BaseModel):
    evidence_type: EvidenceType
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None

class Evidence(EvidenceBase):
    id: int
    finding_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FindingBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: FindingSeverity
    confidence: Optional[FindingConfidence] = None
    category: Optional[str] = None
    location: Optional[str] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    status: FindingStatus = FindingStatus.open
    
    # Risk fields
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    risk_rationale: Optional[str] = None

    # Phase 7 fields
    normalized_category: Optional[str] = None
    normalized_type: Optional[str] = None
    root_cause: Optional[str] = None
    exploitability_context: Optional[str] = None
    evidence_quality: Optional[str] = None
    identity_hash: Optional[str] = None
    scanner_sources: List[str] = Field(default_factory=list)

class Finding(FindingBase):
    id: int
    scan_job_id: int
    created_at: datetime
    updated_at: datetime
    evidence_list: List[Evidence] = Field(default_factory=list)

    class Config:
        from_attributes = True
