from datetime import datetime
from sqlalchemy.orm import Session
from app.models.assessment import ScanJob, Assessment, ScanJobStatus
from .scanners import get_scanner

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
