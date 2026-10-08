import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.assessment import Base, Assessment, ScanJob, Finding, FindingSeverity, FindingStatus, Evidence
from app.main import app
from app.core.database import get_db

class TestAssessmentIsolation(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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

        from app.models.assessment import Project
        self.p = Project(name="Proj")
        self.db.add(self.p)
        self.db.commit()

        # Create Assessment A
        self.assessment_a = Assessment(name="Assessment A", target="10.0.0.1", scope="10.0.0.1", project_id=1, authorization_confirmed=True)
        self.db.add(self.assessment_a)
        
        # Create Assessment B
        self.assessment_b = Assessment(name="Assessment B", target="10.0.0.2", scope="10.0.0.2", project_id=1, authorization_confirmed=True)
        self.db.add(self.assessment_b)
        
        self.db.commit()

        # Job & Finding A
        self.job_a = ScanJob(assessment_id=self.assessment_a.id, scan_profile="standard")
        self.db.add(self.job_a)
        self.db.commit()

        self.finding_a = Finding(scan_job_id=self.job_a.id, title="Vuln A", severity=FindingSeverity.high, status=FindingStatus.open)
        self.db.add(self.finding_a)
        self.db.commit()
        
        self.ev_a = Evidence(finding_id=self.finding_a.id, evidence_type="text", title="Ev A", content="A")
        self.db.add(self.ev_a)
        self.db.commit()

        # Job & Finding B
        self.job_b = ScanJob(assessment_id=self.assessment_b.id, scan_profile="standard")
        self.db.add(self.job_b)
        self.db.commit()

        self.finding_b = Finding(scan_job_id=self.job_b.id, title="Vuln B", severity=FindingSeverity.high, status=FindingStatus.open)
        self.db.add(self.finding_b)
        self.db.commit()
        
        self.ev_b = Evidence(finding_id=self.finding_b.id, evidence_type="text", title="Ev B", content="B")
        self.db.add(self.ev_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_finding_isolation_positive(self):
        # Request finding A in Assessment A -> Success
        resp = self.client.get(f"/api/findings/{self.finding_a.id}?assessment_id={self.assessment_a.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], self.finding_a.id)

    def test_02_finding_isolation_negative(self):
        # Attempt Finding B through Assessment A context -> 404
        resp = self.client.get(f"/api/findings/{self.finding_b.id}?assessment_id={self.assessment_a.id}")
        self.assertEqual(resp.status_code, 404)

    def test_03_evidence_isolation_positive(self):
        resp = self.client.get(f"/api/findings/{self.finding_a.id}/evidence?assessment_id={self.assessment_a.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_04_evidence_isolation_negative(self):
        resp = self.client.get(f"/api/findings/{self.finding_b.id}/evidence?assessment_id={self.assessment_a.id}")
        self.assertEqual(resp.status_code, 404)

if __name__ == '__main__':
    unittest.main()
