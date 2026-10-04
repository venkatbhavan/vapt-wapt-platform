import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Assessment, Project, Finding, ScanJob, FindingSeverity

class TestReportAPI(unittest.TestCase):
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

        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Open Port",
            severity=FindingSeverity.high,
            status="open"
        )
        self.db.add(self.finding)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        app.dependency_overrides.clear()

    def test_create_report(self):
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "My Report"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["title"], "My Report")
        self.assertEqual(data["status"], "generated")
        self.assertNotIn("snapshot", data) # Metadata only

    def test_create_report_unauthorized(self):
        self.assessment.authorization_confirmed = False
        self.db.commit()
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "My Report"})
        self.assertEqual(resp.status_code, 403)

    def test_list_reports(self):
        self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "R1"})
        self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "R2"})
        
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/reports")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        # Check deterministic ordering (descending by created_at)
        self.assertEqual(data[0]["title"], "R2")
        self.assertEqual(data[1]["title"], "R1")
        self.assertNotIn("snapshot", data[0])

    def test_get_report_metadata(self):
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "R1"})
        report_id = resp.json()["id"]
        
        get_resp = self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertEqual(data["title"], "R1")
        self.assertNotIn("snapshot", data)

    def test_get_report_dataset_stability(self):
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "R1"})
        report_id = resp.json()["id"]
        
        # Verify initial dataset
        ds_resp = self.client.get(f"/api/reports/{report_id}/dataset")
        self.assertEqual(ds_resp.status_code, 200)
        dataset = ds_resp.json()
        self.assertEqual(dataset["executive_summary"]["high_findings"], 1)
        self.assertEqual(dataset["technical_findings"][0]["severity"], "high")
        
        # Change the finding severity
        self.finding.severity = FindingSeverity.low
        self.db.commit()
        
        # Get dataset again, it should NOT change
        ds_resp2 = self.client.get(f"/api/reports/{report_id}/dataset")
        dataset2 = ds_resp2.json()
        self.assertEqual(dataset2["executive_summary"]["high_findings"], 1)
        self.assertEqual(dataset2["technical_findings"][0]["severity"], "high")

    def test_report_isolation(self):
        a2 = Assessment(
            project_id=self.project.id,
            name="A2",
            target="10.0.0.1",
            scope="10.0.0.1",
            authorization_confirmed=True
        )
        self.db.add(a2)
        self.db.commit()
        
        # Create report for A1
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/reports", json={"title": "R1"})
        
        # List reports for A2
        list_a2 = self.client.get(f"/api/assessments/{a2.id}/reports")
        self.assertEqual(list_a2.status_code, 200)
        self.assertEqual(len(list_a2.json()), 0)

if __name__ == '__main__':
    unittest.main()