from pydantic import BaseModel
from typing import List

class Finding(BaseModel):
    title: str
    severity: str
    description: str

class ScannerResult(BaseModel):
    scanner: str
    target: str
    scan_profile: str
    findings: List[Finding]
