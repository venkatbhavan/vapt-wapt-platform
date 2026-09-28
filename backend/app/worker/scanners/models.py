from pydantic import BaseModel, Field
from typing import List, Optional

class ScannerError(Exception):
    """Exception raised for scanner-specific errors to be handled by the worker."""
    pass

class EvidenceItem(BaseModel):
    evidence_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None

class Finding(BaseModel):
    title: str
    severity: str
    description: str
    confidence: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)

class ScannerResult(BaseModel):
    scanner: str
    target: str
    scan_profile: str
    findings: List[Finding]
