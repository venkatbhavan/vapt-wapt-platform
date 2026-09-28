from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class ScanProfile(str, enum.Enum):
    passive = "passive"
    safe = "safe"
    standard = "standard"
    deep = "deep"

class AssessmentStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    completed = "completed"
    failed = "failed"

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessments = relationship("Assessment", back_populates="project", cascade="all, delete-orphan")

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    target = Column(String, nullable=False)
    authorization_confirmed = Column(Boolean, nullable=False, default=False)
    scope = Column(String, nullable=False)
    scan_profile = Column(Enum(ScanProfile), default=ScanProfile.passive)
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="assessments")
