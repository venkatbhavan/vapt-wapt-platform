import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.assessment import Base

class ReportStatus(str, enum.Enum):
    draft = "draft"
    generated = "generated"
    failed = "failed"

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.draft, nullable=False)
    share_token = Column(String, unique=True, index=True, nullable=True)
    
    # The generated dataset representing the point-in-time snapshot
    snapshot = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generated_at = Column(DateTime, nullable=True)

    assessment = relationship("Assessment", back_populates="reports")