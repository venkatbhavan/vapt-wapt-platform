from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EvidenceReference(BaseModel):
    entity_type: str = Field(description="Type of entity (finding, asset, network_service, compliance, remediation, retest)")
    entity_id: int = Field(description="The numeric ID of the referenced entity")

class AIAnalystResponse(BaseModel):
    assessment_id: int
    analyst_version: str
    summary: str = Field(description="High-level summary of the security posture based on evidence")
    key_observations: List[str] = Field(description="List of observed facts derived purely from the evidence")
    risk_priorities: List[str] = Field(description="Prioritized risks derived from findings and attack surface")
    correlations: List[str] = Field(description="Inferences and correlations found between different pieces of evidence")
    recommendations: List[str] = Field(description="Actionable recommendations")
    uncertainties: List[str] = Field(description="Areas where evidence is insufficient or where claims cannot be fully supported")
    evidence_references: List[EvidenceReference] = Field(default_factory=list, description="Traceable references to platform evidence")

class AIAnalystRequest(BaseModel):
    assessment_id: int
    analysis_type: str = Field(default="general", description="The type of analysis requested")
    instructions: Optional[str] = Field(default=None, description="Optional extra instructions for the analyst")
