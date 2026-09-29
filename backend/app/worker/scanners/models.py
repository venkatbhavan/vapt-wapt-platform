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

class ServiceObservation(BaseModel):
    port: int
    protocol: str
    state: str
    service_name: Optional[str] = None
    service_product: Optional[str] = None
    service_version: Optional[str] = None
    extra_info: Optional[str] = None

class HostObservation(BaseModel):
    ip_address: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    services: List[ServiceObservation] = Field(default_factory=list)

class ScannerResult(BaseModel):
    scanner: str
    target: str
    scan_profile: str
    findings: List[Finding] = Field(default_factory=list)
    hosts: List[HostObservation] = Field(default_factory=list)
