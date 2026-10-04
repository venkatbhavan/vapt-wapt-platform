from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

class ReportAssessmentScope(BaseModel):
    id: int
    name: str
    target: str
    scope: str
    status: str

class ExecutiveSummary(BaseModel):
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    informational_findings: int
    total_assets: int
    total_network_services: int
    total_web_applications: int
    total_endpoints: int
    total_retests: int
    fixed_findings: int
    still_present_findings: int
    changed_findings: int
    inconclusive_retests: int

class RiskSummary(BaseModel):
    severity_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    risk_level_distribution: Dict[str, int]

class AttackSurfaceSummary(BaseModel):
    asset_types: Dict[str, int]
    service_protocols: Dict[str, int]
    service_states: Dict[str, int]
    web_application_schemes: Dict[str, int]

class FindingsSummary(BaseModel):
    status_distribution: Dict[str, int]
    normalized_category_distribution: Dict[str, int]
    normalized_type_distribution: Dict[str, int]
    scanner_source_distribution: Dict[str, int]

class ComplianceSummary(BaseModel):
    frameworks_represented: int
    controls_represented: int
    mapped_finding_count: int
    mappings_by_framework: Dict[str, int]

class RemediationSummary(BaseModel):
    findings_with_remediation: int
    remediation_guidance_count: int
    priority_distribution: Dict[str, int]
    remediation_type_distribution: Dict[str, int]

class RetestingSummary(BaseModel):
    total_requests: int
    completed: int
    failed: int
    requested_running: int

class TechnicalFinding(BaseModel):
    id: int
    title: str
    severity: str
    confidence: str
    risk_score: float
    risk_level: str
    status: str
    normalized_category: str
    normalized_type: str
    root_cause: str
    exploitability_context: str
    evidence_quality: str
    location: Optional[str]
    scanner_sources: List[str]
    # Mappings
    compliance_controls: List[str] = Field(default_factory=list)
    remediation_guidances: List[str] = Field(default_factory=list)
    retest_history: List[str] = Field(default_factory=list)

class ReportDataset(BaseModel):
    scope: ReportAssessmentScope
    executive_summary: ExecutiveSummary
    risk_summary: RiskSummary
    attack_surface_summary: AttackSurfaceSummary
    findings_summary: FindingsSummary
    compliance_summary: ComplianceSummary
    remediation_summary: RemediationSummary
    retesting_summary: RetestingSummary
    technical_findings: List[TechnicalFinding]

class ReportResponse(BaseModel):
    id: int
    assessment_id: int
    title: str
    status: str
    snapshot: Optional[ReportDataset]
    created_at: datetime
    updated_at: datetime
    generated_at: Optional[datetime]

    class Config:
        orm_mode = True
class ReportCreateRequest(BaseModel):
    title: str = "Assessment Report"

class ReportMetadataResponse(BaseModel):
    id: int
    assessment_id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    generated_at: Optional[datetime]

    class Config:
        orm_mode = True
