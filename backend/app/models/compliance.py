import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from app.models.assessment import Base

class MappingConfidence(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class MappingType(str, enum.Enum):
    direct = "direct"
    related = "related"

class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uix_compliance_framework_name_version"),
    )

    controls = relationship("ComplianceControl", back_populates="framework", cascade="all, delete-orphan")

class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id = Column(Integer, primary_key=True, index=True)
    framework_id = Column(Integer, ForeignKey("compliance_frameworks.id"), nullable=False)
    control_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("framework_id", "control_id", name="uix_compliance_control_framework_control"),
    )

    framework = relationship("ComplianceFramework", back_populates="controls")
    mappings = relationship("FindingComplianceMapping", back_populates="control", cascade="all, delete-orphan")

class FindingComplianceMapping(Base):
    __tablename__ = "finding_compliance_mappings"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    control_id = Column(Integer, ForeignKey("compliance_controls.id"), nullable=False)
    rationale = Column(Text, nullable=False)
    mapping_type = Column(Enum(MappingType), nullable=False)
    mapping_confidence = Column(Enum(MappingConfidence), nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("finding_id", "control_id", name="uix_finding_compliance_mapping_finding_control"),
    )

    finding = relationship("Finding", back_populates="compliance_mappings")
    control = relationship("ComplianceControl", back_populates="mappings")
