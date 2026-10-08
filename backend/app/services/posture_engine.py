from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from collections import defaultdict
import math

from app.models.assessment import Assessment, Finding, ScanJob, FindingStatus, FindingSeverity
from app.models.attack_surface import Asset, NetworkService
from app.models.retest import RetestRequest, RetestStatus, RetestResult, RetestResultStatus
from app.models.compliance import FindingComplianceMapping
from app.models.remediation import FindingRemediation
from app.schemas.posture import PostureResult, PostureLevel, CoverageStatus, PostureDimensions, PostureContributor

METHODOLOGY_VERSION = "1.0"

def get_finding_risk_score(finding: Finding) -> float:
    if finding.risk_score is not None:
        return finding.risk_score
    mapping = {
        FindingSeverity.critical: 4.0,
        FindingSeverity.high: 3.0,
        FindingSeverity.medium: 2.0,
        FindingSeverity.low: 1.0,
        FindingSeverity.info: 0.0
    }
    return mapping.get(finding.severity, 0.0)

def calculate_finding_penalty(score: float) -> float:
    return round(score ** 2.5, 2)

def calculate_posture(db: Session, assessment_id: int) -> PostureResult:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    # Load findings for this assessment
    findings = db.query(Finding).join(ScanJob).filter(ScanJob.assessment_id == assessment_id).all()
    
    # Load assets & network services
    assets = db.query(Asset).filter(Asset.assessment_id == assessment_id).all()
    asset_ids = [a.id for a in assets]
    services = db.query(NetworkService).filter(NetworkService.asset_id.in_(asset_ids)).all() if asset_ids else []

    # Check for NO_DATA
    if not findings:
        return PostureResult(
            assessment_id=assessment_id,
            score=None,
            level=PostureLevel.NO_DATA,
            coverage_status=CoverageStatus.unknown if not assets else CoverageStatus.limited,
            methodology_version=METHODOLOGY_VERSION,
            dimensions=PostureDimensions(
                finding_risk=0.0, finding_health=0.0, attack_surface=0.0, remediation=0.0, compliance=0.0
            ),
            contributors=[],
            generated_at=datetime.utcnow()
        )

    # Initialize dimension penalties
    dim_finding_risk = 0.0
    dim_finding_health = 0.0
    dim_attack_surface = 0.0
    dim_remediation = 0.0
    dim_compliance = 0.0

    contributors = []
    
    # 1. Attack Surface Penalty
    risky_services_count = 0
    risky_protocols = {"telnet", "ftp", "smb", "rdp", "vnc"}
    for svc in services:
        if svc.state.lower() == "open" and svc.service_name and svc.service_name.lower() in risky_protocols:
            risky_services_count += 1
    
    if risky_services_count > 0:
        penalty = risky_services_count * 2.0
        dim_attack_surface += penalty
        contributors.append(PostureContributor(
            category="attack_surface",
            reason=f"{risky_services_count} risky exposed services detected",
            impact=-penalty,
            count=risky_services_count,
            related_finding_ids=[]
        ))

    # Pre-fetch relations we need for findings to avoid N+1 inside the loop
    # We can do this efficiently or just query them since we only need certain things.
    finding_ids = [f.id for f in findings]
    
    # Retesting: load completed retest results
    retests = db.query(RetestRequest).filter(
        RetestRequest.finding_id.in_(finding_ids),
        RetestRequest.status == RetestStatus.completed
    ).options(joinedload(RetestRequest.result)).all()
    
    finding_retests = defaultdict(list)
    for r in retests:
        finding_retests[r.finding_id].append(r)
        
    # Compliance: load compliance mappings
    compliances = db.query(FindingComplianceMapping).filter(FindingComplianceMapping.finding_id.in_(finding_ids)).all()
    finding_compliances = defaultdict(list)
    for c in compliances:
        finding_compliances[c.finding_id].append(c)
        
    # Remediation: load remediation mappings
    remediations = db.query(FindingRemediation).filter(FindingRemediation.finding_id.in_(finding_ids)).all()
    finding_remediations = defaultdict(list)
    for r in remediations:
        finding_remediations[r.finding_id].append(r)

    # Dictionaries to aggregate contributors
    open_findings_by_severity = defaultdict(list)
    still_present_findings = []
    unremediated_critical_high = []
    compliance_violation_findings = []

    for finding in findings:
        # We only penalize active (open) findings for base risk
        if finding.status == FindingStatus.open:
            score = get_finding_risk_score(finding)
            penalty = calculate_finding_penalty(score)
            if penalty > 0:
                dim_finding_risk += penalty
                open_findings_by_severity[finding.severity.value].append(finding.id)
                
            # Check retesting (Finding Health)
            # If there's a completed retest and it's still present, it's worse.
            latest_retest = sorted(finding_retests.get(finding.id, []), key=lambda x: x.created_at, reverse=True)
            if latest_retest:
                if latest_retest[0].result and latest_retest[0].result.result == RetestResultStatus.still_present:
                    still_present_findings.append(finding.id)
                    
            # Check Remediation Health
            if finding.severity in (FindingSeverity.critical, FindingSeverity.high):
                has_guidance = bool(finding_remediations.get(finding.id)) or bool(finding.remediation)
                if not has_guidance:
                    unremediated_critical_high.append(finding.id)
                    
            # Check Compliance Signal
            if finding_compliances.get(finding.id):
                compliance_violation_findings.append(finding.id)

    # Compile finding risk contributors
    for sev, ids in open_findings_by_severity.items():
        # calculate sum of penalty for this severity to show impact
        sev_impact = sum([calculate_finding_penalty(get_finding_risk_score(f)) for f in findings if f.id in ids])
        contributors.append(PostureContributor(
            category="finding_risk",
            reason=f"{len(ids)} open {sev} findings",
            impact=-round(sev_impact, 2),
            count=len(ids),
            related_finding_ids=ids
        ))
        
    # Finding Health contributor
    if still_present_findings:
        penalty = len(still_present_findings) * 5.0
        dim_finding_health += penalty
        contributors.append(PostureContributor(
            category="finding_health",
            reason=f"{len(still_present_findings)} findings still present after retesting",
            impact=-penalty,
            count=len(still_present_findings),
            related_finding_ids=still_present_findings
        ))
        
    # Remediation contributor
    if unremediated_critical_high:
        penalty = len(unremediated_critical_high) * 3.0
        dim_remediation += penalty
        contributors.append(PostureContributor(
            category="remediation",
            reason=f"{len(unremediated_critical_high)} high/critical findings without remediation guidance",
            impact=-penalty,
            count=len(unremediated_critical_high),
            related_finding_ids=unremediated_critical_high
        ))
        
    # Compliance contributor
    if compliance_violation_findings:
        penalty = len(compliance_violation_findings) * 1.0
        dim_compliance += penalty
        contributors.append(PostureContributor(
            category="compliance",
            reason=f"{len(compliance_violation_findings)} open findings violating compliance controls",
            impact=-penalty,
            count=len(compliance_violation_findings),
            related_finding_ids=compliance_violation_findings
        ))

    # Calculate final score
    total_penalty = dim_finding_risk + dim_finding_health + dim_attack_surface + dim_remediation + dim_compliance
    final_score_raw = 100.0 - total_penalty
    
    # Bound between 0 and 100
    final_score = max(0, min(100, int(math.floor(final_score_raw))))
    
    # Determine Level
    if final_score >= 90:
        level = PostureLevel.STRONG
    elif final_score >= 70:
        level = PostureLevel.GOOD
    elif final_score >= 50:
        level = PostureLevel.MODERATE
    elif final_score >= 25:
        level = PostureLevel.WEAK
    else:
        level = PostureLevel.CRITICAL
        
    return PostureResult(
        assessment_id=assessment_id,
        score=final_score,
        level=level,
        coverage_status=CoverageStatus.sufficient,
        methodology_version=METHODOLOGY_VERSION,
        dimensions=PostureDimensions(
            finding_risk=round(dim_finding_risk, 2),
            finding_health=round(dim_finding_health, 2),
            attack_surface=round(dim_attack_surface, 2),
            remediation=round(dim_remediation, 2),
            compliance=round(dim_compliance, 2)
        ),
        contributors=contributors,
        generated_at=datetime.utcnow()
    )
