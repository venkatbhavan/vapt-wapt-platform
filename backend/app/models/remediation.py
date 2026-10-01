import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from app.models.assessment import Base

class RemediationType(str, enum.Enum):
    configuration = "configuration"
    code = "code"
    dependency = "dependency"
    access_control = "access_control"
    cryptography = "cryptography"
    network = "network"
    architecture = "architecture"
    unknown = "unknown"

class RemediationPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class RemediationMappingConfidence(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class RemediationGuidance(Base):
    __tablename__ = "remediation_guidance"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    detailed_guidance = Column(Text, nullable=False)
    remediation_type = Column(Enum(RemediationType), nullable=False)
    priority = Column(Enum(RemediationPriority), nullable=False)
    verification_guidance = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    finding_mappings = relationship("FindingRemediation", back_populates="remediation_guidance", cascade="all, delete-orphan")


class FindingRemediation(Base):
    __tablename__ = "finding_remediations"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False, index=True)
    remediation_guidance_id = Column(Integer, ForeignKey("remediation_guidance.id"), nullable=False, index=True)
    rationale = Column(Text, nullable=False)
    mapping_confidence = Column(Enum(RemediationMappingConfidence), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("finding_id", "remediation_guidance_id", name="uix_finding_remediation_guidance"),
    )

    finding = relationship("Finding", back_populates="remediation_mappings")
    remediation_guidance = relationship("RemediationGuidance", back_populates="finding_mappings")
