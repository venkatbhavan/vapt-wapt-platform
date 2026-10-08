import unittest
import json
import re
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Finding, Project, ScanJob, Assessment
from app.models.attack_surface import Asset
from app.models.assessment import Assessment

from app.models.report import Report, ReportStatus
from app.services.report_engine import generate_report
from datetime import datetime

# Setup test DB
from sqlalchemy.pool import StaticPool


class TestReportExport(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()
        
        def override_get_db():
            try:
                yield self.db
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)


        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()

        self.assessment = Assessment(
            project_id=self.project.id,
            name="Test Assessment",
            target="192.168.1.0/24",
            scope="192.168.1.1",
            authorization_confirmed=True
        )
        self.db.add(self.assessment)
        self.db.commit()
        
        self.scan_job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(self.scan_job)
        self.db.commit()

        self.asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.1")
        self.db.add(self.asset)
        self.db.commit()
        
        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Open Port",
            severity="medium",
            confidence="high",
            risk_score=5.5,
            risk_level="medium",
            status="open",
            asset_id=self.asset.id,
            normalized_type="open_port",
            scanner_sources=["nmap"]
        )
        self.db.add(self.finding)
        self.db.commit()

    
        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title='Test Finding <script>alert("xss")</script>',
            description='Description <img src="x" onerror="alert(1)">',
            severity="critical",
            confidence="high",
            status="open",
            category="Injection"
        )
        self.db.add(self.finding)
        self.db.commit()
        
        self.report = generate_report(self.db, self.assessment.id, "Malicious Title <script>alert()</script>")

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_export_html_security_and_format(self):
        """Verify HTML export escapes dangerous content and has correct MIME."""
        response = self.client.get(f"/api/reports/{self.report.id}/export/html?assessment_id={self.assessment.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        self.assertIn("attachment; filename=", response.headers["content-disposition"])
        
        html_content = response.text
        self.assertIn("HISTORICAL REPORT SNAPSHOT", html_content)
        
        # Check XSS was escaped
        self.assertNotIn('<script>alert("xss")</script>', html_content)
        self.assertNotIn('<script>alert()</script>', html_content)
        self.assertIn('&lt;script&gt;alert(', html_content)

    def test_export_pdf_format(self):
        """Verify PDF export returns valid PDF blob."""
        response = self.client.get(f"/api/reports/{self.report.id}/export/pdf?assessment_id={self.assessment.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("attachment; filename=", response.headers["content-disposition"])
        
        # Check PDF signature
        pdf_bytes = response.content
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1."))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_snapshot_immutability(self):
        """Verify exported HTML content reflects original snapshot despite DB changes."""
        
        # Modify DB finding
        self.finding.severity = "low"
        self.db.commit()
        
        # Request HTML export
        response = self.client.get(f"/api/reports/{self.report.id}/export/html?assessment_id={self.assessment.id}")
        self.assertEqual(response.status_code, 200)
        
        html_content = response.text
        # Original snapshot had 1 critical finding and 0 low findings
        # The HTML should STILL show Critical: 1 and Low: 0
        self.assertIn("Critical Findings", html_content)
        self.assertTrue(re.search(r'Critical Findings.*?<div[^>]*>1</div>', html_content, re.DOTALL))

    def test_404_not_found(self):
        response = self.client.get(f"/api/reports/999/export/html?assessment_id={self.assessment.id}")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
