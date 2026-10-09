from app.core.database import SessionLocal
from app.models.assessment import Assessment, ScanJob, ScanJobStatus
from app.worker.service import process_scan_job
from app.worker.scanners.models import ScannerResult, Finding, WebApplicationObservation, WebEndpointObservation, HostObservation, ServiceObservation
from unittest.mock import patch
from app.core.init_db import init_db
from app.models.assessment import Project

init_db()
db = SessionLocal()

try:
    project = db.query(Project).filter(Project.name == "Test Project").first()
    if not project:
        project = Project(name="Test Project")
        db.add(project)
        db.commit()
        db.refresh(project)

    assessment = db.query(Assessment).filter(Assessment.name == "Phase 6F E2E Test", Assessment.project_id == project.id).first()
    if not assessment:
        assessment = Assessment(name="Phase 6F E2E Test", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    nmap_job = db.query(ScanJob).filter(ScanJob.assessment_id == assessment.id, ScanJob.scan_profile == "standard").first()
    if not nmap_job:
        nmap_job = ScanJob(assessment_id=assessment.id, scan_profile="standard")
        db.add(nmap_job)
        db.commit()
        db.refresh(nmap_job)

    zap_job = db.query(ScanJob).filter(ScanJob.assessment_id == assessment.id, ScanJob.scan_profile == "passive").first()
    if not zap_job:
        zap_job = ScanJob(assessment_id=assessment.id, scan_profile="passive")
        db.add(zap_job)
        db.commit()
        db.refresh(zap_job)

    nmap_res = ScannerResult(
        scanner="nmap", target="127.0.0.1", scan_profile="standard",
        hosts=[HostObservation(
            ip_address="127.0.0.1", hostname="localhost",
            services=[
                ServiceObservation(port=80, protocol="tcp", state="open", service_name="http"),
                ServiceObservation(port=443, protocol="tcp", state="open", service_name="https")
            ]
        )],
        findings=[Finding(title="Open Port 80", severity="info", description="Port open", confidence="high", location="127.0.0.1:80/tcp")]
    )

    zap_res = ScannerResult(
        scanner="zap", target="127.0.0.1", scan_profile="passive",
        web_applications=[
            WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80, title="Test App", tech_info="React",
                endpoints=[
                    WebEndpointObservation(url="http://127.0.0.1:80/api/users", path="/api/users", method="GET")
                ]
            )
        ],
        findings=[
            Finding(title="XSS Found", severity="high", description="Cross site scripting on /api/users", confidence="high", location="http://127.0.0.1:80/api/users"),
            Finding(title="Missing Security Headers", severity="low", description="HSTS missing", confidence="medium", location="http://127.0.0.1:80")
        ]
    )

    def mock_get_scanner_nmap(scanner_name):
        class MockScanner:
            def scan(self, target, scan_profile): return nmap_res
        return MockScanner()

    def mock_get_scanner_zap(scanner_name):
        class MockScanner:
            def scan(self, target, scan_profile): return zap_res
        return MockScanner()

    if nmap_job.status != ScanJobStatus.completed:
        with patch('app.worker.service.get_scanner', side_effect=mock_get_scanner_nmap):
            process_scan_job(db, nmap_job.id)

    if zap_job.status != ScanJobStatus.completed:
        with patch('app.worker.service.get_scanner', side_effect=mock_get_scanner_zap):
            process_scan_job(db, zap_job.id)

    print(f"Data Seeded. Assessment ID: {assessment.id}")
except Exception as e:
    db.rollback()
    print(f"Failed to seed demo data: {e}")
    import sys
    sys.exit(1)
finally:
    db.close()
