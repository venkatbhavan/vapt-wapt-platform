from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean, Float
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class ScanProfile(str, enum.Enum):
    passive = "passive"
    safe = "safe"
    standard = "standard"
    active = "active"
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
    scan_jobs = relationship("ScanJob", back_populates="assessment", cascade="all, delete-orphan")

class ScanJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class ScanJob(Base):
    __tablename__ = "scan_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    scan_profile = Column(Enum(ScanProfile), nullable=False)
    active_scan_confirmed = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(ScanJobStatus), default=ScanJobStatus.queued)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    result_json = Column(String, nullable=True)

    assessment = relationship("Assessment", back_populates="scan_jobs")
    findings = relationship("Finding", back_populates="scan_job", cascade="all, delete-orphan")

class FindingSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class FindingConfidence(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class FindingStatus(str, enum.Enum):
    open = "open"
    accepted = "accepted"
    false_positive = "false_positive"
    resolved = "resolved"

class EvidenceType(str, enum.Enum):
    text = "text"
    http_request = "http_request"
    http_response = "http_response"
    command_output = "command_output"
    screenshot = "screenshot"
    metadata = "metadata"

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    severity = Column(Enum(FindingSeverity), nullable=False)
    confidence = Column(Enum(FindingConfidence), nullable=True)
    category = Column(String, nullable=True)
    location = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    remediation = Column(String, nullable=True)
    status = Column(Enum(FindingStatus), default=FindingStatus.open)
    
    # Risk Engine Fields
    from app.risk.models import RiskLevel
    risk_score = Column(Float, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    risk_rationale = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scan_job = relationship("ScanJob", back_populates="findings")
    evidence_list = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    evidence_type = Column(Enum(EvidenceType), nullable=False)
    title = Column(String, nullable=True)
    content = Column(String, nullable=True) # E.g. raw text, JSON string, or a path/identifier for screenshots
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("Finding", back_populates="evidence_list")

