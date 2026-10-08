import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.assessment import Assessment, Finding, ScanJob
from app.models.attack_surface import Asset, NetworkService
from app.models.compliance import FindingComplianceMapping
from app.models.remediation import FindingRemediation
from app.models.retest import RetestRequest
from app.services.posture_engine import calculate_posture
import logging

logger = logging.getLogger(__name__)

# Basic deterministic sanitizer for sensitive fields
# Limitation: This relies on simple regex/keyword matching and will not catch every secret.
# It is designed to redact obvious credential-like patterns in raw output.
def sanitize_text(text: str) -> str:
    if not text:
        return ""
    # Redact common authorization headers
    text = re.sub(r'(?i)(Authorization:\s*Bearer\s+)[a-zA-Z0-9_\-\.]+', r'\1[REDACTED]', text)
    # Redact obvious AWS keys
    text = re.sub(r'(?i)(AKIA[0-9A-Z]{16})', r'[REDACTED_AWS_KEY]', text)
    # Redact basic passwords in URIs
    text = re.sub(r'(?i)(://[^:]+:)([^@]+)(@)', r'\1[REDACTED]\3', text)
    return text

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = {}
    for k, v in data.items():
        if isinstance(v, str):
            sanitized[k] = sanitize_text(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_text(i) if isinstance(i, str) else (sanitize_dict(i) if isinstance(i, dict) else i) for i in v]
        else:
            sanitized[k] = v
    return sanitized

def build_analyst_context(db: Session, assessment_id: int, max_findings: int = 50) -> Dict[str, Any]:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    context: Dict[str, Any] = {
        "assessment_id": assessment_id,
        "assessment_name": assessment.name,
        "target": assessment.target,
        "scope": assessment.scope,
    }

    try:
        posture = calculate_posture(db, assessment_id)
        context["posture"] = {
            "score": posture.score,
            "level": posture.level.value,
            "coverage_status": posture.coverage_status.value
        }
    except Exception as e:
        logger.warning(f"Could not calculate posture for context: {e}")
        context["posture"] = None

    # Gather Findings
    # Prioritize active/open findings with the highest risk score
    # Ordering: open first, then by risk_score desc
    findings = db.query(Finding).join(ScanJob).filter(ScanJob.assessment_id == assessment_id)\
        .order_by(Finding.status, Finding.risk_score.desc()).limit(max_findings).all()

    context["findings"] = []
    finding_ids = set()
    for f in findings:
        finding_ids.add(f.id)
        context["findings"].append(sanitize_dict({
            "id": f.id,
            "title": f.title,
            "severity": f.severity.value if hasattr(f.severity, 'value') else f.severity,
            "risk_score": f.risk_score,
            "status": f.status.value if hasattr(f.status, 'value') else f.status,
            "description": f.description
        }))

    # Attack surface: limit to 50 assets
    assets = db.query(Asset).filter(Asset.assessment_id == assessment_id).limit(50).all()
    asset_ids = [a.id for a in assets]
    
    services = []
    if asset_ids:
        services = db.query(NetworkService).filter(NetworkService.asset_id.in_(asset_ids)).limit(100).all()

    context["attack_surface"] = {
        "assets": [{"id": a.id, "ip": a.ip_address, "hostname": a.hostname, "status": a.status.value if hasattr(a.status, 'value') else a.status} for a in assets],
        "services": [{"id": s.id, "asset_id": s.asset_id, "port": s.port, "protocol": s.protocol, "service_name": s.service_name, "state": s.state} for s in services]
    }

    # Compliance
    compliance_mappings = db.query(FindingComplianceMapping).filter(FindingComplianceMapping.finding_id.in_(finding_ids)).all()
    context["compliance"] = [{"finding_id": c.finding_id, "control_id": c.control_id, "mapping_type": c.mapping_type.value if hasattr(c.mapping_type, 'value') else c.mapping_type} for c in compliance_mappings]

    # Remediation
    remediations = db.query(FindingRemediation).filter(FindingRemediation.finding_id.in_(finding_ids)).all()
    context["remediation"] = [{"finding_id": r.finding_id, "recommendation": sanitize_text(r.recommendation)} for r in remediations]

    # Retesting
    retests = db.query(RetestRequest).filter(RetestRequest.finding_id.in_(finding_ids)).all()
    context["retesting"] = []
    for r in retests:
        status = r.status.value if hasattr(r.status, 'value') else r.status
        result_status = None
        if r.result:
            result_status = r.result.result.value if hasattr(r.result.result, 'value') else r.result.result
        context["retesting"].append({
            "finding_id": r.finding_id,
            "request_status": status,
            "result": result_status
        })

    return context
