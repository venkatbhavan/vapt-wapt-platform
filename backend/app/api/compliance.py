from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.models.assessment import Assessment, ScanJob, Finding
from app.models.compliance import FindingComplianceMapping, ComplianceControl, ComplianceFramework
from app.schemas.compliance import (
    ComplianceAssessmentResponse,
    ComplianceFrameworkResponse,
    ComplianceControlResponse,
    ComplianceMappingResponse
)

router = APIRouter(tags=["compliance"])

@router.get("/api/assessments/{assessment_id}/compliance", response_model=ComplianceAssessmentResponse)
def get_assessment_compliance(assessment_id: int, db: Session = Depends(get_db)):
    # 1. Verify Assessment exists
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        
    # 2. Efficiently query all relevant mappings by isolating to assessment_id through ScanJob and Finding
    # We use joinedload to avoid N+1 queries.
    mappings = (
        db.query(FindingComplianceMapping)
        .join(Finding)
        .join(ScanJob)
        .join(ComplianceControl)
        .join(ComplianceFramework)
        .filter(ScanJob.assessment_id == assessment_id)
        .options(
            joinedload(FindingComplianceMapping.finding),
            joinedload(FindingComplianceMapping.control).joinedload(ComplianceControl.framework)
        )
        .all()
    )

    if not mappings:
        return ComplianceAssessmentResponse(
            assessment_id=assessment_id,
            frameworks=[]
        )

    # 3. Build response deterministically
    frameworks_dict = {}

    for mapping in mappings:
        fw = mapping.control.framework
        ctrl = mapping.control
        f_id = fw.id
        c_id = ctrl.id

        if f_id not in frameworks_dict:
            frameworks_dict[f_id] = {
                "id": fw.id,
                "name": fw.name,
                "version": fw.version,
                "description": fw.description,
                "controls_dict": {},
                "_fw_obj": fw
            }

        if c_id not in frameworks_dict[f_id]["controls_dict"]:
            frameworks_dict[f_id]["controls_dict"][c_id] = {
                "id": ctrl.id,
                "control_id": ctrl.control_id,
                "title": ctrl.title,
                "description": ctrl.description,
                "mappings": [],
                "_ctrl_obj": ctrl
            }

        # Add the mapping
        frameworks_dict[f_id]["controls_dict"][c_id]["mappings"].append(
            ComplianceMappingResponse(
                id=mapping.id,
                finding_id=mapping.finding.id,
                finding_title=mapping.finding.title,
                finding_severity=mapping.finding.severity.value if hasattr(mapping.finding.severity, 'value') else mapping.finding.severity,
                finding_status=mapping.finding.status.value if hasattr(mapping.finding.status, 'value') else mapping.finding.status,
                mapping_type=mapping.mapping_type.value if hasattr(mapping.mapping_type, 'value') else mapping.mapping_type,
                mapping_confidence=mapping.mapping_confidence.value if hasattr(mapping.mapping_confidence, 'value') else mapping.mapping_confidence,
                rationale=mapping.rationale,
                source=mapping.source
            )
        )

    # Sort logic to make it deterministic
    # frameworks by: name, version
    sorted_fws = sorted(
        frameworks_dict.values(),
        key=lambda f: (f["name"], f["version"])
    )

    response_frameworks = []
    for fw_data in sorted_fws:
        # controls by: control_id
        sorted_ctrls = sorted(
            fw_data["controls_dict"].values(),
            key=lambda c: c["control_id"]
        )

        response_controls = []
        for ctrl_data in sorted_ctrls:
            # mappings by: finding_id, id
            sorted_mappings = sorted(
                ctrl_data["mappings"],
                key=lambda m: (m.finding_id, m.id)
            )

            response_controls.append(
                ComplianceControlResponse(
                    id=ctrl_data["id"],
                    control_id=ctrl_data["control_id"],
                    title=ctrl_data["title"],
                    description=ctrl_data["description"],
                    mappings=sorted_mappings
                )
            )

        response_frameworks.append(
            ComplianceFrameworkResponse(
                id=fw_data["id"],
                name=fw_data["name"],
                version=fw_data["version"],
                description=fw_data["description"],
                controls=response_controls
            )
        )

    return ComplianceAssessmentResponse(
        assessment_id=assessment_id,
        frameworks=response_frameworks
    )
