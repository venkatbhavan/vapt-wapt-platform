import unittest
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Assessment, Project, Finding, ScanJob
from app.models.report import Report, ReportStatus
from app.models.report_share import ReportShareLink
from app.services.report_engine import generate_report

class TestReportShareHardened(unittest.TestCase):
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

    def test_share_report_hardened(self):
        # Create share
        future = datetime.now(timezone.utc) + timedelta(days=1)
        response = self.client.post(
            f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}",
            json={"expires_at": future.isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIsNotNone(data.get("share_url"))
        share_url = data["share_url"]
        raw_token = share_url.split("/")[-1]
        share_id = data["id"]

        # Verify raw token is NOT in database
        share_link = self.db.query(ReportShareLink).filter(ReportShareLink.id == share_id).first()
        self.assertIsNotNone(share_link)
        self.assertNotEqual(share_link.token_hash, raw_token)

        # Verify correct hashing
        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        self.assertEqual(share_link.token_hash, expected_hash)

        # Verify unauthenticated endpoint works
        shared_response = self.client.get(f"/api/shared/reports/{raw_token}")
        self.assertEqual(shared_response.status_code, 200)
        shared_data = shared_response.json()
        self.assertEqual(shared_data["title"], "Test Report")

        # Verify access count incremented
        self.db.refresh(share_link)
        self.assertEqual(share_link.access_count, 1)
        self.assertIsNotNone(share_link.last_accessed_at)

    def test_multiple_shares_and_revoke(self):
        # Create share A
        resp_a = self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={})
        token_a = resp_a.json()["share_url"].split("/")[-1]
        share_id_a = resp_a.json()["id"]

        # Create share B
        resp_b = self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={})
        token_b = resp_b.json()["share_url"].split("/")[-1]

        # Revoke A
        revoke_resp = self.client.post(f"/api/shares/{share_id_a}/revoke?assessment_id={self.assessment.id}")
        self.assertEqual(revoke_resp.status_code, 200)

        # Access A should fail
        self.assertEqual(self.client.get(f"/api/shared/reports/{token_a}").status_code, 404)

        # Access B should succeed
        self.assertEqual(self.client.get(f"/api/shared/reports/{token_b}").status_code, 200)

    def test_expired_share(self):
        # Create share that expired yesterday
        past = datetime.now(timezone.utc) - timedelta(days=1)
        resp = self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={"expires_at": past.isoformat()})
        token = resp.json()["share_url"].split("/")[-1]

        self.assertEqual(self.client.get(f"/api/shared/reports/{token}").status_code, 404)

    def test_snapshot_immutability(self):
        resp = self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={})
        token = resp.json()["share_url"].split("/")[-1]

        initial = self.client.get(f"/api/shared/reports/{token}").json()
        self.assertEqual(initial["snapshot"]["executive_summary"]["critical_findings"], 1)

        # Modify DB finding
        self.finding.severity = "low"
        self.db.commit()

        # Snapshot must be unchanged
        subsequent = self.client.get(f"/api/shared/reports/{token}").json()
        self.assertEqual(subsequent["snapshot"]["executive_summary"]["critical_findings"], 1)

    def test_list_shares(self):
        self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={})
        self.client.post(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}", json={})

        resp = self.client.get(f"/api/reports/{self.report.id}/shares?assessment_id={self.assessment.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)
        # Verify raw token is NOT in the list response
        self.assertIsNone(resp.json()[0].get("share_url"))
        self.assertNotIn("token_hash", resp.json()[0])

if __name__ == "__main__":
    unittest.main()
