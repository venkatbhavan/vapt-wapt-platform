import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.core.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity
from app.models.retest import RetestRequest, RetestStatus, RetestResult, RetestResultStatus, RetestConfidence

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestRetestAPI(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.client = TestClient(app)
        
        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()
        
        self.assessment_A = Assessment(
            project_id=self.project.id,
            name="Assessment A",
            target="10.0.0.1",
            scan_profile="standard",
            status="running",
            authorization_confirmed=True,
            scope="external"
        )
        self.assessment_B = Assessment(
            project_id=self.project.id,
            name="Assessment B",
            target="10.0.0.2",
            scan_profile="standard",
            status="running",
            authorization_confirmed=True,
            scope="external"
        )
        self.db.add_all([self.assessment_A, self.assessment_B])
        self.db.commit()
        
        self.scan_job_A = ScanJob(assessment_id=self.assessment_A.id, scan_profile="standard", active_scan_confirmed=True)
        self.scan_job_B = ScanJob(assessment_id=self.assessment_B.id, scan_profile="standard", active_scan_confirmed=True)
        self.db.add_all([self.scan_job_A, self.scan_job_B])
        self.db.commit()
        
        self.finding_A = Finding(scan_job_id=self.scan_job_A.id, title="FA", severity=FindingSeverity.low, normalized_type="test")
        self.finding_B = Finding(scan_job_id=self.scan_job_B.id, title="FB", severity=FindingSeverity.low, normalized_type="test")
        self.db.add_all([self.finding_A, self.finding_B])
        self.db.commit()
        
    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    @patch('app.api.retests.run_retest')
    def test_create_retest_success(self, mock_run_retest):
        def fake_run(db, req_id):
            req = db.query(RetestRequest).get(req_id)
            req.status = RetestStatus.completed
            res = RetestResult(retest_request_id=req_id, previous_finding_id=req.finding_id, result=RetestResultStatus.fixed, confidence=RetestConfidence.high, rationale="ok")
            db.add(res)
            db.commit()
            return req
            
        mock_run_retest.side_effect = fake_run
        
        response = self.client.post(f"/api/findings/{self.finding_A.id}/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["finding_id"], self.finding_A.id)
        self.assertEqual(data["status"], "completed")
        self.assertIsNotNone(data["result"])
        self.assertEqual(data["result"]["result"], "fixed")
        
    def test_create_retest_not_found(self):
        response = self.client.post(f"/api/findings/999/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 404)
        
    def test_create_retest_unauthorized(self):
        self.assessment_A.authorization_confirmed = False
        self.db.commit()
        response = self.client.post(f"/api/findings/{self.finding_A.id}/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 403)
        
    def test_get_finding_retests(self):
        # Create a few retests manually
        r1 = RetestRequest(finding_id=self.finding_A.id, status=RetestStatus.completed)
        from app.models.retest import RetestResult, RetestResultStatus, RetestConfidence
        from app.models.assessment import Evidence, EvidenceType
        res1 = RetestResult(retest_request_id=r1.id, previous_finding_id=self.finding_A.id, result=RetestResultStatus.still_present, confidence=RetestConfidence.high, rationale="x")
        ev = Evidence(evidence_type=EvidenceType.text, title="Proof API")
        res1.evidence.append(ev)
        r1.result = res1
        r2 = RetestRequest(finding_id=self.finding_A.id, status=RetestStatus.completed)
        self.db.add_all([r1, r2])
        self.db.commit()
        
        response = self.client.get(f"/api/findings/{self.finding_A.id}/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        
    def test_get_finding_retests_empty_and_not_found(self):
        response = self.client.get(f"/api/findings/{self.finding_A.id}/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        
        response2 = self.client.get(f"/api/findings/999/retests?assessment_id={self.assessment_A.id}")
        self.assertEqual(response2.status_code, 404)
        
    def test_get_retest_by_id(self):
        r1 = RetestRequest(finding_id=self.finding_A.id, status=RetestStatus.completed)
        from app.models.retest import RetestResult, RetestResultStatus, RetestConfidence
        from app.models.assessment import Evidence, EvidenceType
        res1 = RetestResult(retest_request_id=r1.id, previous_finding_id=self.finding_A.id, result=RetestResultStatus.still_present, confidence=RetestConfidence.high, rationale="x")
        ev = Evidence(evidence_type=EvidenceType.text, title="Proof API")
        res1.evidence.append(ev)
        r1.result = res1
        self.db.add(r1)
        self.db.commit()
        
        response = self.client.get(f"/api/retests/{r1.id}?assessment_id={self.assessment_A.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], r1.id)
        self.assertEqual(len(response.json()["result"]["evidence"]), 1)
        self.assertEqual(response.json()["result"]["evidence"][0]["title"], "Proof API")
        
        response2 = self.client.get(f"/api/retests/999?assessment_id={self.assessment_A.id}")
        self.assertEqual(response2.status_code, 404)
        
    def test_assessment_isolation(self):
        rA = RetestRequest(finding_id=self.finding_A.id, status=RetestStatus.requested)
        rB = RetestRequest(finding_id=self.finding_B.id, status=RetestStatus.requested)
        self.db.add_all([rA, rB])
        self.db.commit()
        
        response_A = self.client.get(f"/api/assessments/{self.assessment_A.id}/retests")
        self.assertEqual(response_A.status_code, 200)
        data_A = response_A.json()
        self.assertEqual(len(data_A), 1)
        self.assertEqual(data_A[0]["id"], rA.id)
        
        response_B = self.client.get(f"/api/assessments/{self.assessment_B.id}/retests")
        self.assertEqual(response_B.status_code, 200)
        data_B = response_B.json()
        self.assertEqual(len(data_B), 1)
        self.assertEqual(data_B[0]["id"], rB.id)

    def test_get_assessment_not_found(self):
        response = self.client.get("/api/assessments/999/retests")
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
