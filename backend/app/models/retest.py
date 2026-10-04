import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from app.models.assessment import Base
class RetestStatus(str, enum.Enum):
    requested = "requested"
    running = "running"
    completed = "completed"
    failed = "failed"
class RetestResultStatus(str, enum.Enum):
    fixed = "fixed"
    still_present = "still_present"
    changed = "changed"
    inconclusive = "inconclusive"
class RetestConfidence(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
class RetestRequest(Base):
    __tablename__ = "retest_requests"
    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), index=True, nullable=False)
    status = Column(Enum(RetestStatus), index=True, nullable=False, default=RetestStatus.requested)
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    finding = relationship("Finding", back_populates="retest_requests")
    result = relationship("RetestResult", back_populates="retest_request", uselist=False, cascade="all, delete-orphan")
class RetestResult(Base):
    __tablename__ = "retest_results"
    id = Column(Integer, primary_key=True, index=True)
    retest_request_id = Column(Integer, ForeignKey("retest_requests.id"), index=True, nullable=False)
    previous_finding_id = Column(Integer, ForeignKey("findings.id"), index=True, nullable=False)
    current_finding_id = Column(Integer, ForeignKey("findings.id"), index=True, nullable=True)
    result = Column(Enum(RetestResultStatus), index=True, nullable=False)
    confidence = Column(Enum(RetestConfidence), nullable=False)
    rationale = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    retest_request = relationship("RetestRequest", back_populates="result")
    previous_finding = relationship("Finding", foreign_keys=[previous_finding_id])
    current_finding = relationship("Finding", foreign_keys=[current_finding_id])
    evidence = relationship("Evidence", back_populates="retest_result", cascade="all, delete-orphan")