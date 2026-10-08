from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from app.models.assessment import ScanProfile, AssessmentStatus

class AssessmentBase(BaseModel):
    name: str = Field(..., min_length=1, description="Assessment name must not be empty")
    target: str = Field(..., min_length=1, description="Target must not be empty")
    scope: str = Field(..., min_length=1, description="Scope must not be empty")

    @validator("target")
    def check_target(cls, v):
        # Reject values that scanners could misread as command-line options
        # (e.g. "-iL /etc/hosts" or "--script=...") or that contain whitespace/control characters.
        v = v.strip()
        if not v:
            raise ValueError("Target must not be empty")
        if v.startswith("-"):
            raise ValueError("Target must not start with '-'")
        if any(ch.isspace() or ord(ch) < 32 for ch in v):
            raise ValueError("Target must not contain whitespace or control characters")
        return v

class AssessmentCreate(AssessmentBase):
    authorization_confirmed: bool = Field(..., description="Must explicitly confirm authorization")
    
    @validator("authorization_confirmed")
    def check_authorization(cls, v):
        if not v:
            raise ValueError("Authorization must be confirmed")
        return v

class Assessment(AssessmentBase):
    id: int
    project_id: int
    authorization_confirmed: bool
    scan_profile: ScanProfile
    status: AssessmentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
