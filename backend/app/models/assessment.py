from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class ScanProfile(enum.Enum):
    PASSIVE = "Passive"
    SAFE = "Safe"
    STANDARD = "Standard"
    DEEP = "Deep"

class AssessmentStatus(enum.Enum):
    DRAFT = "Draft"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    target = Column(String, nullable=False)
    scope_rules = Column(String, nullable=False) # Simplified for Phase 1
    scan_profile = Column(Enum(ScanProfile), default=ScanProfile.PASSIVE)
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
