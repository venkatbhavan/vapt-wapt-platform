import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.assessment import Base, Project, Assessment, ScanJob, ScanProfile, Finding, Evidence

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_findings_persistence():
    db = SessionLocal()
    try:
        # Seed test data
        project = Project(name="Finding Test Project")
        db.add(project)
        db.commit()
        db.refresh(project)

        assessment = Assessment(
            project_id=project.id,
            name="Finding Assessment",
            target="http://example.com",
            scope="Everything",
            authorization_confirmed=True
        )
        db.add(assessment)
        db.commit()

        job = ScanJob(assessment_id=assessment.id, scan_profile=ScanProfile.passive)
        db.add(job)
        db.commit()

        from app.worker.service import process_scan_job
        import app.worker.service
        from app.worker.scanners.mock import MockScannerAdapter

        # Explicit dependency injection via patching for this test
        app.worker.service.get_scanner = lambda profile: MockScannerAdapter()

        completed_job = process_scan_job(db, job.id)

        # Verify findings were created
        findings = db.query(Finding).filter(Finding.scan_job_id == completed_job.id).all()
        assert len(findings) == 1
        finding = findings[0]
        assert finding.title == "Mock Security Finding"
        assert finding.severity == "low"
        assert finding.risk_score == 0.75 # low(1) * default medium(0.75)
        assert finding.risk_level == "low"
        assert "Confidence was not provided" in finding.risk_rationale

        # Verify evidence was created
        evidence_list = db.query(Evidence).filter(Evidence.finding_id == finding.id).all()
        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.evidence_type == "text"
        assert evidence.title == "Mock Evidence"
        assert evidence.source == "mock"

        # Verify cascade deletion
        db.delete(completed_job)
        db.commit()

        findings_after = db.query(Finding).filter(Finding.scan_job_id == completed_job.id).all()
        assert len(findings_after) == 0

        evidence_after = db.query(Evidence).filter(Evidence.finding_id == finding.id).all()
        assert len(evidence_after) == 0

        print("Findings persistence tests passed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    test_findings_persistence()
