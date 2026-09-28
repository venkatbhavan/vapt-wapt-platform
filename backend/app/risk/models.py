import enum
from pydantic import BaseModel

class RiskLevel(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class RiskResult(BaseModel):
    score: float
    level: RiskLevel
    rationale: str
