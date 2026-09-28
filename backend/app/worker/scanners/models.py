from pydantic import BaseModel, Field
from typing import List, Optional

class EvidenceItem(BaseModel):
    evidence_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None

class Finding(BaseModel):
    title: str
    severity: str
    description: str
    evidence: List[EvidenceItem] = Field(default_factory=list)

class ScannerResult(BaseModel):
    scanner: str
    target: str
    scan_profile: str
    findings: List[Finding]
