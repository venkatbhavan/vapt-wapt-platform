from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from collections import Counter
from app.models.assessment import Assessment, Finding, ScanJob
from app.models.attack_surface import Asset
from app.models.attack_surface import NetworkService, WebApplication, WebEndpoint
from app.models.compliance import FindingComplianceMapping, ComplianceControl, ComplianceFramework
from app.models.remediation import FindingRemediation, RemediationGuidance
from app.models.retest import RetestRequest, RetestResult
from app.models.report import Report, ReportStatus
from app.schemas.report import (
    ReportAssessmentScope, ExecutiveSummary, RiskSummary, AttackSurfaceSummary,
    FindingsSummary, ComplianceSummary, RemediationSummary, RetestingSummary,
    TechnicalFinding, ReportDataset
)

def generate_report_dataset(db: Session, assessment_id: int) -> ReportDataset:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    # 1. Assessment / Scope
    scope = ReportAssessmentScope(
        id=assessment.id,
        name=assessment.name,
        target=assessment.target,
        scope=assessment.scope,
        status=assessment.status.value
    )

    # Fetch findings with eager loading
    findings = db.query(Finding).join(ScanJob).filter(ScanJob.assessment_id == assessment_id).options(
        joinedload(Finding.compliance_mappings).joinedload(FindingComplianceMapping.control).joinedload(ComplianceControl.framework),
        joinedload(Finding.remediation_mappings).joinedload(FindingRemediation.remediation_guidance),
        joinedload(Finding.retest_requests).joinedload(RetestRequest.result)
    ).all()

    # Fetch attack surface
    assets = db.query(Asset).filter(Asset.assessment_id == assessment_id).options(
        joinedload(Asset.services),
        joinedload(Asset.web_applications).joinedload(WebApplication.endpoints)
    ).all()
    
    # 2. Executive Summary Metrics
    total_findings = len(findings)
    severity_counts = Counter(f.severity.value for f in findings)
    
    services = [s for a in assets for s in a.services]
    web_apps = [w for a in assets for w in a.web_applications]
    endpoints = [e for w in web_apps for e in w.endpoints]
    
    retest_requests = [r for f in findings for r in f.retest_requests]
    retest_results = [r.result for r in retest_requests if r.result]

    exec_summary = ExecutiveSummary(
        total_findings=total_findings,
        critical_findings=severity_counts.get("critical", 0),
        high_findings=severity_counts.get("high", 0),
        medium_findings=severity_counts.get("medium", 0),
        low_findings=severity_counts.get("low", 0),
        informational_findings=severity_counts.get("info", 0),
        total_assets=len(assets),
        total_network_services=len(services),
        total_web_applications=len(web_apps),
        total_endpoints=len(endpoints),
        total_retests=len(retest_requests),
        fixed_findings=sum(1 for r in retest_results if r.result.value == "fixed"),
        still_present_findings=sum(1 for r in retest_results if r.result.value == "still_present"),
        changed_findings=sum(1 for r in retest_results if r.result.value == "changed"),
        inconclusive_retests=sum(1 for r in retest_results if r.result.value == "inconclusive")
    )

    # 3. Risk Summary
    risk_summary = RiskSummary(
        severity_distribution=dict(severity_counts),
        confidence_distribution=dict(Counter(f.confidence.value if f.confidence else "unknown" for f in findings)),
        risk_level_distribution=dict(Counter(f.risk_level for f in findings if f.risk_level))
    )

    # 4. Attack Surface Summary
    attack_surface_summary = AttackSurfaceSummary(
        asset_types=dict(Counter(a.asset_type for a in assets if hasattr(a, 'asset_type') and a.asset_type)),
        service_protocols=dict(Counter(s.protocol for s in services if s.protocol)),
        service_states=dict(Counter(s.state for s in services if s.state)),
        web_application_schemes=dict(Counter(w.scheme for w in web_apps if w.scheme))
    )

    # 5. Findings Summary
    findings_summary = FindingsSummary(
        status_distribution=dict(Counter(f.status.value for f in findings)),
        normalized_category_distribution=dict(Counter(f.normalized_category for f in findings if f.normalized_category)),
        normalized_type_distribution=dict(Counter(f.normalized_type for f in findings if f.normalized_type)),
        scanner_source_distribution=dict(Counter(src for f in findings if f.scanner_sources for src in f.scanner_sources))
    )

    # 6. Compliance Summary
    all_mappings = [m for f in findings for m in f.compliance_mappings]
    frameworks = {m.control.framework.name for m in all_mappings if m.control and m.control.framework}
    controls = {m.control.id for m in all_mappings if m.control}
    framework_counts = Counter(m.control.framework.name for m in all_mappings if m.control and m.control.framework)
    
    compliance_summary = ComplianceSummary(
        frameworks_represented=len(frameworks),
        controls_represented=len(controls),
        mapped_finding_count=len({m.finding_id for m in all_mappings}),
        mappings_by_framework=dict(framework_counts)
    )

    # 7. Remediation Summary
    all_rem_mappings = [m for f in findings for m in f.remediation_mappings]
    guidance_set = {m.remediation_guidance.id for m in all_rem_mappings if m.remediation_guidance}
    
    remediation_summary = RemediationSummary(
        findings_with_remediation=len({m.finding_id for m in all_rem_mappings}),
        remediation_guidance_count=len(guidance_set),
        priority_distribution=dict(Counter(m.remediation_guidance.priority.value for m in all_rem_mappings if m.remediation_guidance and m.remediation_guidance.priority)),
        remediation_type_distribution=dict(Counter(m.remediation_guidance.remediation_type.value for m in all_rem_mappings if m.remediation_guidance and m.remediation_guidance.remediation_type))
    )

    # 8. Retesting Summary
    retesting_summary = RetestingSummary(
        total_requests=len(retest_requests),
        completed=sum(1 for r in retest_requests if r.status.value == "completed"),
        failed=sum(1 for r in retest_requests if r.status.value == "failed"),
        requested_running=sum(1 for r in retest_requests if r.status.value in ("requested", "running"))
    )

    # 9. Technical Findings
    technical_findings = []
    # Sort findings for determinism
    findings.sort(key=lambda f: (f.severity.value, f.id))
    
    for f in findings:
        comp_controls = sorted(list(set(f"{m.control.framework.name} {m.control.control_id}" for m in f.compliance_mappings if m.control and m.control.framework)))
        rem_guides = sorted(list(set(m.remediation_guidance.title for m in f.remediation_mappings if m.remediation_guidance)))
        
        f.retest_requests.sort(key=lambda r: r.requested_at)
        retests_hist = [f"Retest {r.id}: {r.status.value}" + (f" ({r.result.result.value})" if r.result else "") for r in f.retest_requests]
        
        tf = TechnicalFinding(
            id=f.id,
            title=f.title,
            severity=f.severity.value,
            confidence=f.confidence.value if f.confidence else "unknown",
            risk_score=float(f.risk_score) if f.risk_score is not None else 0.0,
            risk_level=f.risk_level or "none",
            status=f.status.value,
            normalized_category=f.normalized_category or "unknown",
            normalized_type=f.normalized_type or "unknown",
            root_cause=f.root_cause or "unknown",
            exploitability_context=f.exploitability_context or "unknown",
            evidence_quality=f.evidence_quality or "unknown",
            location=f.location,
            scanner_sources=f.scanner_sources or [],
            compliance_controls=comp_controls,
            remediation_guidances=rem_guides,
            retest_history=retests_hist
        )
        technical_findings.append(tf)

    return ReportDataset(
        scope=scope,
        executive_summary=exec_summary,
        risk_summary=risk_summary,
        attack_surface_summary=attack_surface_summary,
        findings_summary=findings_summary,
        compliance_summary=compliance_summary,
        remediation_summary=remediation_summary,
        retesting_summary=retesting_summary,
        technical_findings=technical_findings
    )

def generate_report(db: Session, assessment_id: int, title: str) -> Report:
    dataset = generate_report_dataset(db, assessment_id)
    
    report = Report(
        assessment_id=assessment_id,
        title=title,
        status=ReportStatus.generated,
        snapshot=dataset.dict(),
        generated_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
