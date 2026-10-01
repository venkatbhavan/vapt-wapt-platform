from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.assessment import Assessment, ScanJob, Finding
from app.models.remediation import FindingRemediation, RemediationGuidance
from app.schemas.remediation import (
    AssessmentRemediationResponse,
    RemediationGuidanceWithMappings,
    RemediationMappingDetail,
    RemediationMappingFinding
)

router = APIRouter(tags=["remediation"])

# Priority and Severity mapping for deterministic sorting
PRIORITY_ORDER = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4
}

SEVERITY_ORDER = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "info": 5
}

@router.get("/api/assessments/{assessment_id}/remediation", response_model=AssessmentRemediationResponse)
def get_assessment_remediation(assessment_id: int, db: Session = Depends(get_db)):
    # 1. Verify Assessment exists
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # 2. Efficiently query all relevant mappings by isolating to assessment_id
    mappings = (
        db.query(FindingRemediation)
        .join(Finding)
        .join(ScanJob)
        .filter(ScanJob.assessment_id == assessment_id)
        .options(
            joinedload(FindingRemediation.finding),
            joinedload(FindingRemediation.remediation_guidance)
        )
        .all()
    )

    if not mappings:
        return AssessmentRemediationResponse(
            assessment_id=assessment_id,
            remediations=[]
        )

    # 3. Build response deterministically grouped by RemediationGuidance
    remediations_dict = {}

    for mapping in mappings:
        guidance = mapping.remediation_guidance
        g_id = guidance.id

        if g_id not in remediations_dict:
            remediations_dict[g_id] = {
                "id": guidance.id,
                "title": guidance.title,
                "summary": guidance.summary,
                "detailed_guidance": guidance.detailed_guidance,
                "remediation_type": guidance.remediation_type.value if hasattr(guidance.remediation_type, 'value') else guidance.remediation_type,
                "priority": guidance.priority.value if hasattr(guidance.priority, 'value') else guidance.priority,
                "verification_guidance": guidance.verification_guidance,
                "mappings": []
            }

        finding = mapping.finding

        remediations_dict[g_id]["mappings"].append(
            RemediationMappingDetail(
                id=mapping.id,
                finding=RemediationMappingFinding(
                    id=finding.id,
                    title=finding.title,
                    severity=finding.severity.value if hasattr(finding.severity, 'value') else finding.severity,
                    status=finding.status.value if hasattr(finding.status, 'value') else finding.status,
                    normalized_type=finding.normalized_type
                ),
                mapping_confidence=mapping.mapping_confidence.value if hasattr(mapping.mapping_confidence, 'value') else mapping.mapping_confidence,
                rationale=mapping.rationale
            )
        )

    # Sort logic to make it deterministic
    # RemediationGuidance: 1. priority 2. title 3. id
    sorted_remediations = sorted(
        remediations_dict.values(),
        key=lambda r: (
            PRIORITY_ORDER.get(r["priority"], 99),
            r["title"],
            r["id"]
        )
    )

    response_remediations = []
    for r_data in sorted_remediations:
        # Mappings: 1. finding severity 2. finding title 3. finding id
        sorted_mappings = sorted(
            r_data["mappings"],
            key=lambda m: (
                SEVERITY_ORDER.get(m.finding.severity, 99),
                m.finding.title,
                m.finding.id
            )
        )

        r_data["mappings"] = sorted_mappings
        response_remediations.append(RemediationGuidanceWithMappings(**r_data))

    return AssessmentRemediationResponse(
        assessment_id=assessment_id,
        remediations=response_remediations
    )
