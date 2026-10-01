from sqlalchemy.orm import Session
from app.models.assessment import Finding
from app.models.remediation import (
    RemediationGuidance,
    FindingRemediation,
    RemediationType,
    RemediationPriority,
    RemediationMappingConfidence
)
from app.worker.remediation.catalog import REMEDIATION_CATALOG

def map_finding_to_remediation(db: Session, finding: Finding) -> None:
    """
    Idempotently maps a normalized Finding to its corresponding remediation guidance based on the deterministic catalog.
    Unknown or unmapped normalized finding types yield no action.
    """
    if not finding.normalized_type or finding.normalized_type == "unknown":
        return

    # 1. Gather explicit catalog mappings for this normalized_type
    matched_entries = [entry for entry in REMEDIATION_CATALOG if entry["normalized_type"] == finding.normalized_type]

    if not matched_entries:
        return

    for entry in matched_entries:
        title = entry["title"]

        # 2. Resolve or create RemediationGuidance based on the deterministic title
        guidance = db.query(RemediationGuidance).filter(
            RemediationGuidance.title == title
        ).first()

        if not guidance:
            remediation_type_val = entry["remediation_type"]
            remediation_type_enum = getattr(RemediationType, remediation_type_val, RemediationType.unknown)

            priority_val = entry["priority"]
            priority_enum = getattr(RemediationPriority, priority_val, RemediationPriority.low)

            guidance = RemediationGuidance(
                title=title,
                summary=entry["summary"],
                detailed_guidance=entry["detailed_guidance"],
                remediation_type=remediation_type_enum,
                priority=priority_enum,
                verification_guidance=entry["verification_guidance"]
            )
            db.add(guidance)
            db.flush()

        # 3. Resolve or create FindingRemediation
        mapping = db.query(FindingRemediation).filter(
            FindingRemediation.finding_id == finding.id,
            FindingRemediation.remediation_guidance_id == guidance.id
        ).first()

        if not mapping:
            confidence_val = entry["mapping_confidence"]
            confidence_enum = getattr(RemediationMappingConfidence, confidence_val, RemediationMappingConfidence.low)

            mapping = FindingRemediation(
                finding_id=finding.id,
                remediation_guidance_id=guidance.id,
                rationale=entry["rationale"],
                mapping_confidence=confidence_enum
            )
            db.add(mapping)
            db.flush()
