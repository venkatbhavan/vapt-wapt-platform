from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.assessment import ScanProfile, ScanJobStatus

class ScanJob(BaseModel):
    id: int
    assessment_id: int
    scan_profile: ScanProfile
    status: ScanJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
