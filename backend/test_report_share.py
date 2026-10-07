import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Assessment, Project, Finding, ScanJob
from app.models.report import Report, ReportStatus
from app.services.report_engine import generate_report

class TestReportShare(unittest.TestCase):
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

        # Setup test data
        self.project = Project(name="Test Proj")
        self.db.add(self.project)
        self.db.commit()
        
        self.assessment = Assessment(
            project_id=self.project.id,
            name="Export Test Assessment",
            target="https://export-target.com",
            scope="everything",
            authorization_confirmed=True
        )
        self.db.add(self.assessment)
        self.db.commit()
        self.db.refresh(self.assessment)
        
        self.scan_job = ScanJob(assessment_id=self.assessment.id, scan_profile="passive", status="completed")
        self.db.add(self.scan_job)
        self.db.commit()
        self.db.refresh(self.scan_job)
        
        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title='Test Finding',
            severity="critical",
            status="open"
        )
        self.db.add(self.finding)
        self.db.commit()
        
        self.report = generate_report(self.db, self.assessment.id, "Test Report")
        
    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_share_report(self):
        # Initial share token should be None
        self.assertIsNone(self.report.share_token)
        
        # Share the report
        response = self.client.post(f"/api/reports/{self.report.id}/share")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsNotNone(data.get("share_token"))
        token = data["share_token"]
        
        # Verify unauthenticated endpoint returns the report snapshot
        shared_response = self.client.get(f"/api/shared/reports/{token}")
        self.assertEqual(shared_response.status_code, 200)
        shared_data = shared_response.json()
        self.assertEqual(shared_data["title"], "Test Report")
        self.assertIsNotNone(shared_data["snapshot"])
        self.assertEqual(shared_data["snapshot"]["executive_summary"]["critical_findings"], 1)

    def test_unshare_report(self):
        # First share it
        response = self.client.post(f"/api/reports/{self.report.id}/share")
        token = response.json()["share_token"]
        
        # Now unshare it
        unshare_response = self.client.post(f"/api/reports/{self.report.id}/unshare")
        self.assertEqual(unshare_response.status_code, 200)
        self.assertIsNone(unshare_response.json().get("share_token"))
        
        # Verify unauthenticated endpoint returns 404
        shared_response = self.client.get(f"/api/shared/reports/{token}")
        self.assertEqual(shared_response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
