from pydantic import BaseModel

class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

class RiskCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

class StatusCounts(BaseModel):
    open: int = 0
    accepted: int = 0
    false_positive: int = 0
    resolved: int = 0

class ScanJobCounts(BaseModel):
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0

class AssessmentSummary(BaseModel):
    assessment_id: int
    total_findings: int
    severity_counts: SeverityCounts
    risk_counts: RiskCounts
    status_counts: StatusCounts
    scan_job_counts: ScanJobCounts
