from sqlalchemy.orm import Session
from app.models.assessment import Finding
from app.models.compliance import (
    ComplianceFramework,
    ComplianceControl,
    FindingComplianceMapping,
    MappingConfidence,
    MappingType
)
from app.worker.compliance.catalog import COMPLIANCE_MAPPING_CATALOG

def map_finding_to_compliance(db: Session, finding: Finding) -> None:
    """
    Idempotently maps a normalized Finding to its corresponding compliance controls based on the deterministic catalog.
    Unknown or unmapped normalized finding types yield no action.
    """
    if not finding.normalized_type or finding.normalized_type == "unknown":
        return

    # 1. Gather all explicit catalog mappings for this normalized_type
    matched_entries = [entry for entry in COMPLIANCE_MAPPING_CATALOG if entry["normalized_type"] == finding.normalized_type]

    if not matched_entries:
        return

    for entry in matched_entries:
        fw_name = entry["framework_name"]
        fw_version = entry["framework_version"]
        ctrl_id = entry["control_id"]

        # 2. Resolve or create Framework
        fw = db.query(ComplianceFramework).filter(
            ComplianceFramework.name == fw_name,
            ComplianceFramework.version == fw_version
        ).first()

        if not fw:
            fw = ComplianceFramework(
                name=fw_name,
                version=fw_version
            )
            db.add(fw)
            db.flush()

        # 3. Resolve or create Control
        ctrl = db.query(ComplianceControl).filter(
            ComplianceControl.framework_id == fw.id,
            ComplianceControl.control_id == ctrl_id
        ).first()

        if not ctrl:
            ctrl = ComplianceControl(
                framework_id=fw.id,
                control_id=ctrl_id,
                title=entry["control_title"]
            )
            db.add(ctrl)
            db.flush()

        # 4. Resolve or create Mapping
        mapping = db.query(FindingComplianceMapping).filter(
            FindingComplianceMapping.finding_id == finding.id,
            FindingComplianceMapping.control_id == ctrl.id
        ).first()

        if not mapping:
            # Map the confidence correctly to enum
            confidence_val = entry["mapping_confidence"]
            confidence_enum = getattr(MappingConfidence, confidence_val, MappingConfidence.low)

            # Map the type correctly to enum
            type_val = entry["mapping_type"]
            type_enum = getattr(MappingType, type_val, MappingType.related)

            mapping = FindingComplianceMapping(
                finding_id=finding.id,
                control_id=ctrl.id,
                rationale=entry["rationale"],
                mapping_type=type_enum,
                mapping_confidence=confidence_enum,
                source=entry["source"]
            )
            db.add(mapping)
            # Flush is strictly optional here since it's the last step in the loop, but good practice
            db.flush()
