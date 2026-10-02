from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.assessment import ScanJob, Assessment, Finding as DbFinding, ScanJobStatus
from app.models.retest import RetestRequest, RetestResult, RetestStatus, RetestResultStatus, RetestConfidence
from app.worker.scanners import get_scanner
from app.worker.correlation.correlator import correlate_finding
from app.worker.intelligence.normalizer import normalize_finding
from app.worker.intelligence.identity import build_identity_payload, compute_identity_hash
from app.worker.scanners.models import ScannerResult

def resolve_scanner_name(scan_job: ScanJob) -> Optional[str]:
    # Derives the scanner name deterministically from the scan profile
    # The existing codebase maps profiles to scanners.
    # In process_scan_job, it uses get_scanner(scan_job.scan_profile).
    # Then it does: scanner_source_name = (getattr(result, "scanner", None) or "unknown").lower()
    return None

def process_retest_findings(
    db: Session,
    assessment: Assessment,
    scan_job: ScanJob,
    raw_result: ScannerResult,
    original_finding: DbFinding
) -> RetestResult:
    """
    Processes the raw scanner result, generates canonical identities for all findings,
    and compares them to the original finding to determine the retest outcome.
    """
    scanner_source_name = (getattr(raw_result, "scanner", None) or "unknown").lower()

    retest_findings = []
    
    # 1. Generate identity for all new findings without persisting them yet
    # We must not persist them blindly as they belong to a retest, not a normal scan job
    for f_data in raw_result.findings:
        # A. Create temp finding
        temp_finding = DbFinding(
            title=f_data.title,
            location=getattr(f_data, 'location', None)
        )
        
        # B. Correlate to get context
        c_res = correlate_finding(db, assessment.id, temp_finding)
        if c_res.match_type != "none":
            temp_finding.asset_id = c_res.asset_id
            temp_finding.network_service_id = c_res.network_service_id
            temp_finding.web_application_id = c_res.web_application_id
            temp_finding.web_endpoint_id = c_res.web_endpoint_id
            
        # Attach objects for payload builder
        if temp_finding.web_endpoint_id:
            from app.models.attack_surface import WebEndpoint
            temp_finding.web_endpoint = db.query(WebEndpoint).get(temp_finding.web_endpoint_id)
        elif temp_finding.web_application_id:
            from app.models.attack_surface import WebApplication
            temp_finding.web_application = db.query(WebApplication).get(temp_finding.web_application_id)
        elif temp_finding.network_service_id:
            from app.models.attack_surface import NetworkService
            temp_finding.network_service = db.query(NetworkService).get(temp_finding.network_service_id)
        elif temp_finding.asset_id:
            from app.models.attack_surface import Asset
            temp_finding.asset = db.query(Asset).get(temp_finding.asset_id)
            
        # C. Normalize
        intel = normalize_finding(scanner_source_name, f_data)
        
        # D. Identity
        identity_payload = build_identity_payload(assessment.id, intel["normalized_type"], temp_finding)
        identity_hash = compute_identity_hash(identity_payload)
        
        temp_finding.identity_hash = identity_hash
        temp_finding.normalized_type = intel["normalized_type"]
        temp_finding.severity = f_data.severity
        temp_finding.confidence = intel["confidence"]
        
        # Keep track of raw data for creating a new finding if necessary
        retest_findings.append({
            "temp_finding": temp_finding,
            "raw_data": f_data,
            "intel": intel,
            "identity_hash": identity_hash
        })
        
    # 2. Compare against original finding
    exact_match = next((f for f in retest_findings if f["identity_hash"] == original_finding.identity_hash), None)
    
    if exact_match:
        # CASE 1 — STILL PRESENT
        return RetestResult(
            result=RetestResultStatus.still_present,
            confidence=RetestConfidence.high,
            rationale="The exact canonical finding identity was observed during the retest.",
            previous_finding_id=original_finding.id,
            current_finding_id=original_finding.id
        )
        
    # CASE 3 — CHANGED
    # If same normalized_type and same primary asset, but identity_hash differs (e.g., path changed, port changed)
    changed_match = None
    if original_finding.normalized_type != "unknown":
        for f in retest_findings:
            if f["temp_finding"].normalized_type == original_finding.normalized_type:
                # Require strict asset match
                if original_finding.asset_id and f["temp_finding"].asset_id == original_finding.asset_id:
                    changed_match = f
                    break
                    
    if changed_match:
        # Create the new finding for the changed context
        from app.models.assessment import FindingSeverity
        severity_mapped = changed_match["raw_data"].severity if hasattr(FindingSeverity, changed_match["raw_data"].severity) else "info"
        intel = changed_match["intel"]
        
        from app.risk.engine import calculate_risk
        risk_result = calculate_risk(severity_mapped, intel["confidence"])
        
        new_finding = DbFinding(
            scan_job_id=scan_job.id, # Link to original scan job or keep None? The prompt says "associated with the same assessment and created through existing path"
            title=changed_match["raw_data"].title,
            description=changed_match["raw_data"].description,
            severity=severity_mapped,
            confidence=intel["confidence"],
            category=intel["normalized_category"],
            location=getattr(changed_match["raw_data"], 'location', None),
            impact=intel["impact"],
            remediation=intel["remediation"],
            risk_score=risk_result.score,
            risk_level=risk_result.level,
            risk_rationale=risk_result.rationale,
            asset_id=changed_match["temp_finding"].asset_id,
            network_service_id=changed_match["temp_finding"].network_service_id,
            web_application_id=changed_match["temp_finding"].web_application_id,
            web_endpoint_id=changed_match["temp_finding"].web_endpoint_id,
            normalized_category=intel["normalized_category"],
            normalized_type=intel["normalized_type"],
            root_cause=intel["root_cause"],
            exploitability_context=intel["exploitability_context"],
            evidence_quality=intel["evidence_quality"],
            identity_hash=changed_match["identity_hash"],
            scanner_sources=[scanner_source_name]
        )
        db.add(new_finding)
        db.flush() # Ensure ID is generated
        
        return RetestResult(
            result=RetestResultStatus.changed,
            confidence=RetestConfidence.medium,
            rationale="A related finding with the same vulnerability type but different canonical identity was observed on the same asset.",
            previous_finding_id=original_finding.id,
            current_finding_id=new_finding.id
        )
        
    # CASE 2 — FIXED
    return RetestResult(
        result=RetestResultStatus.fixed,
        confidence=RetestConfidence.high,
        rationale="The retest completed successfully and the original canonical finding identity was not observed.",
        previous_finding_id=original_finding.id,
        current_finding_id=None
    )


def run_retest(db: Session, retest_request_id: int) -> RetestRequest:
    # 1. Load RetestRequest
    request = db.query(RetestRequest).filter(RetestRequest.id == retest_request_id).first()
    if not request:
        raise ValueError("RetestRequest not found")
        
    if request.status != RetestStatus.requested:
        raise ValueError(f"Cannot run retest in state: {request.status}")
        
    # 2. Load original Finding
    finding = request.finding
    if not finding:
        raise ValueError("Original Finding not found")
        
    # 3. Load ScanJob
    scan_job = finding.scan_job
    if not scan_job:
        raise ValueError("Original ScanJob not found")
        
    # 4. Load Parent Assessment
    assessment = scan_job.assessment
    if not assessment:
        raise ValueError("Original Assessment not found")
        
    # 5. Authorization & Scope Safety Check
    if not assessment.authorization_confirmed:
        raise ValueError("Assessment authorization not confirmed")

    # Mark as running
    request.status = RetestStatus.running
    request.started_at = datetime.utcnow()
    db.commit()
    
    try:
        # Determine Scanner
        # Reuse the existing scanner context from the original scan_job
        scanner = get_scanner(scan_job.scan_profile)
        if not scanner:
            raise ValueError(f"Scanner profile '{scan_job.scan_profile}' could not be resolved.")
            
        # Execute the existing scanner infrastructure against the original authorized target/scope
        # Do not allow arbitrary target replacement. Use the exact assessment target.
        raw_result = scanner.scan(target=assessment.target, scan_profile=scan_job.scan_profile)
        
        if not getattr(raw_result, 'findings', None) and not raw_result.findings == []:
            # Scanner returned an inconclusive/failed structural response
            raise ValueError("Scanner produced malformed or incomplete results.")
            
        # Process Retest Outcomes
        retest_result = process_retest_findings(
            db=db,
            assessment=assessment,
            scan_job=scan_job,
            raw_result=raw_result,
            original_finding=finding
        )
        
        retest_result.retest_request_id = request.id
        db.add(retest_result)
        
        # Complete
        request.status = RetestStatus.completed
        request.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(request)
        
    except Exception as e:
        # Scanner failure, timeout, parsing failure, infrastructure error -> Inconclusive / Failed
        db.rollback() # Rollback any partial findings or objects safely
        
        # Now mark as failed
        # Since we rolled back, we need to refresh or fetch the request again
        request = db.query(RetestRequest).filter(RetestRequest.id == retest_request_id).first()
        
        request.status = RetestStatus.failed
        request.completed_at = datetime.utcnow()
        
        # Create a failed/inconclusive retest result
        failure_result = RetestResult(
            retest_request_id=request.id,
            previous_finding_id=finding.id,
            result=RetestResultStatus.inconclusive,
            confidence=RetestConfidence.low,
            rationale=f"Retest failed or was inconclusive due to an infrastructure or scanner error: {str(e)}"
        )
        db.add(failure_result)
        db.commit()
        db.refresh(request)
        
    return request
