from datetime import datetime
from sqlalchemy.orm import Session
from app.models.assessment import ScanJob, Assessment, ScanJobStatus
from .scanners import get_scanner
from app.core.database import SessionLocal

def process_scan_job(db: Session, scan_job_id: int) -> ScanJob:
    # 1. Load ScanJob
    scan_job = db.query(ScanJob).filter(ScanJob.id == scan_job_id).first()
    if not scan_job:
        raise ValueError("ScanJob not found")

    # 2. Verify status is queued
    if scan_job.status != ScanJobStatus.queued:
        raise ValueError(f"Cannot run job in state: {scan_job.status}")

    # 3. Load Parent Assessment
    assessment = db.query(Assessment).filter(Assessment.id == scan_job.assessment_id).first()
    if not assessment:
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = "Parent Assessment not found"
        scan_job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(scan_job)
        raise ValueError("Parent Assessment not found")

    # 4. Independent Authorization Check
    if not assessment.authorization_confirmed:
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = "Authorization not confirmed on parent Assessment"
        scan_job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(scan_job)
        raise ValueError("Authorization not confirmed")

    # 5. Transition to Running
    scan_job.status = ScanJobStatus.running
    scan_job.started_at = datetime.utcnow()
    db.commit()

    # 6. Execute Scanner Adapter
    try:
        scanner = get_scanner(scan_job.scan_profile)
        result = scanner.scan(target=assessment.target, scan_profile=scan_job.scan_profile)
        
        # Persist Findings and Evidence
        from app.models.assessment import Finding as FindingModel, FindingSeverity, Evidence as EvidenceModel, EvidenceType
        from app.risk.engine import calculate_risk
        
        for f_data in result.findings:
            severity_mapped = f_data.severity if hasattr(FindingSeverity, f_data.severity) else "info"
            
            # Extract confidence if available; mock scanner doesn't produce it currently, but handle safely
            confidence = getattr(f_data, 'confidence', None)
            risk_result = calculate_risk(severity_mapped, confidence)
            
            db_finding = FindingModel(
                scan_job_id=scan_job.id,
                title=f_data.title,
                description=f_data.description,
                severity=severity_mapped,
                risk_score=risk_result.score,
                risk_level=risk_result.level,
                risk_rationale=risk_result.rationale
            )
            db.add(db_finding)
            db.flush() # flush to get the finding id

            for e_data in f_data.evidence:
                evidence_type_mapped = e_data.evidence_type if hasattr(EvidenceType, e_data.evidence_type) else "text"
                db_evidence = EvidenceModel(
                    finding_id=db_finding.id,
                    evidence_type=evidence_type_mapped,
                    title=e_data.title,
                    content=e_data.content,
                    source=e_data.source
                )
                db.add(db_evidence)

            
        # 7. Transition to Completed
        scan_job.status = ScanJobStatus.completed
        scan_job.result_json = result.model_dump_json()
        scan_job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        # 8. Transition to Failed on internal error
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = f"Scanner error: {str(e)}"
        scan_job.completed_at = datetime.utcnow()
        db.commit()

    db.refresh(scan_job)
    return scan_job

def run_scan_job_background(scan_job_id: int):
    """
    Background wrapper to safely execute a scan job using its own database session.
    """
    db = SessionLocal()
    try:
        process_scan_job(db, scan_job_id)
    except Exception as e:
        # Errors handled gracefully by process_scan_job, but catch unexpected failures here just in case.
        print(f"Background task execution aborted for Job ID {scan_job_id}: {e}")
    finally:
        db.close()
