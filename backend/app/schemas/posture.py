import enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PostureLevel(str, enum.Enum):
    STRONG = "strong"
    GOOD = "good"
    MODERATE = "moderate"
    WEAK = "weak"
    CRITICAL = "critical"
    NO_DATA = "no_data"

class CoverageStatus(str, enum.Enum):
    sufficient = "sufficient"
    limited = "limited"
    unknown = "unknown"

class PostureContributor(BaseModel):
    category: str
    reason: str
    impact: float
    count: int
    related_finding_ids: List[int] = Field(default_factory=list)

class PostureDimensions(BaseModel):
    finding_risk: float
    finding_health: float
    attack_surface: float
    remediation: float
    compliance: float

class PostureResult(BaseModel):
    assessment_id: int
    score: Optional[int]
    level: PostureLevel
    coverage_status: CoverageStatus
    methodology_version: str
    dimensions: PostureDimensions
    contributors: List[PostureContributor]
    generated_at: datetime
