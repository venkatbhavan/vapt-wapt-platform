import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity
from app.models.remediation import RemediationGuidance, FindingRemediation, RemediationType, RemediationPriority, RemediationMappingConfidence
from app.worker.remediation.mapper import map_finding_to_remediation

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestRemediationAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

        # Clean DB
        for tbl in reversed(Base.metadata.sorted_tables):
            self.db.execute(tbl.delete())
        self.db.commit()

        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.flush()

        self.assessment = Assessment(project_id=self.project.id, name="Test Assessment", target="127.0.0.1", scope="local")
        self.assessment2 = Assessment(project_id=self.project.id, name="Other Assessment", target="10.0.0.1", scope="local")
        self.db.add_all([self.assessment, self.assessment2])
        self.db.flush()

        self.job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.job2 = ScanJob(assessment_id=self.assessment2.id, scan_profile="standard")
        self.db.add_all([self.job, self.job2])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _create_finding(self, scan_job_id, title, normalized_type, severity=FindingSeverity.high):
        f = Finding(scan_job_id=scan_job_id, title=title, severity=severity, normalized_type=normalized_type)
        self.db.add(f)
        self.db.commit()
        self.db.refresh(f)
        return f

    def test_01_existing_assessment_with_remediation(self):
        f = self._create_finding(self.job.id, "Test finding", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(len(data["remediations"]), 0)

    def test_02_nonexistent_assessment(self):
        resp = self.client.get("/api/assessments/999/remediation")
        self.assertEqual(resp.status_code, 404)

    def test_03_existing_assessment_no_remediation(self):
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["remediations"]), 0)

    def test_04_assessment_id_returned(self):
        f = self._create_finding(self.job.id, "Test finding", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        self.assertEqual(resp.json()["assessment_id"], self.assessment.id)

    def test_05_to_08_remediation_guidance_fields(self):
        f = self._create_finding(self.job.id, "Test finding", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        r = resp.json()["remediations"][0]

        self.assertIn("id", r)
        self.assertEqual(r["title"], "Use Parameterized Database Queries")
        self.assertIn("summary", r)
        self.assertIn("detailed_guidance", r)
        self.assertEqual(r["remediation_type"], "code")
        self.assertEqual(r["priority"], "critical")
        self.assertIn("verification_guidance", r)

    def test_09_multiple_findings_one_guidance(self):
        f1 = self._create_finding(self.job.id, "F1", "sql_injection")
        f2 = self._create_finding(self.job.id, "F2", "sql_injection")
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f2)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        data = resp.json()
        self.assertEqual(len(data["remediations"]), 1)
        self.assertEqual(len(data["remediations"][0]["mappings"]), 2)

    def test_10_to_16_mapping_and_finding_fields(self):
        f = self._create_finding(self.job.id, "F1", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        mapping = resp.json()["remediations"][0]["mappings"][0]

        self.assertIn("id", mapping)
        self.assertEqual(mapping["mapping_confidence"], "high")
        self.assertIn("rationale", mapping)

        finding = mapping["finding"]
        self.assertEqual(finding["id"], f.id)
        self.assertEqual(finding["title"], "F1")
        self.assertEqual(finding["severity"], "high")
        self.assertEqual(finding["status"], "open")
        self.assertEqual(finding["normalized_type"], "sql_injection")

    def test_17_raw_evidence_not_returned(self):
        f = self._create_finding(self.job.id, "F1", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        mapping = resp.json()["remediations"][0]["mappings"][0]
        finding = mapping["finding"]
        self.assertNotIn("evidence", finding)
        self.assertNotIn("evidence_list", finding)

    def test_18_assessment_isolation(self):
        f1 = self._create_finding(self.job.id, "F1", "sql_injection")
        f2 = self._create_finding(self.job2.id, "F2", "sql_injection")
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f2)
        self.db.commit()

        resp1 = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        mappings1 = resp1.json()["remediations"][0]["mappings"]
        self.assertEqual(len(mappings1), 1)
        self.assertEqual(mappings1[0]["finding"]["id"], f1.id)

        resp2 = self.client.get(f"/api/assessments/{self.assessment2.id}/remediation")
        mappings2 = resp2.json()["remediations"][0]["mappings"]
        self.assertEqual(len(mappings2), 1)
        self.assertEqual(mappings2[0]["finding"]["id"], f2.id)

    def test_19_duplicate_mappings_not_returned(self):
        f = self._create_finding(self.job.id, "F1", "sql_injection")
        map_finding_to_remediation(self.db, f)
        map_finding_to_remediation(self.db, f)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        self.assertEqual(len(resp.json()["remediations"][0]["mappings"]), 1)

    def test_20_multiple_guidance_records_grouped(self):
        f1 = self._create_finding(self.job.id, "F1", "sql_injection")
        f2 = self._create_finding(self.job.id, "F2", "missing_security_headers")
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f2)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        data = resp.json()
        self.assertEqual(len(data["remediations"]), 2)

    def test_21_deterministic_ordering(self):
        f1 = self._create_finding(self.job.id, "C", "missing_security_headers", FindingSeverity.medium)
        f2 = self._create_finding(self.job.id, "A", "sql_injection", FindingSeverity.low)
        f3 = self._create_finding(self.job.id, "B", "sql_injection", FindingSeverity.critical)
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f2)
        map_finding_to_remediation(self.db, f3)
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/remediation")
        data = resp.json()["remediations"]

        # Priority order: sql_injection (critical) > missing_security_headers (high)
        self.assertEqual(data[0]["title"], "Use Parameterized Database Queries")
        self.assertEqual(data[1]["title"], "Configure HTTP Security Headers")

        # Mappings ordering for sql_injection: severity (critical > low)
        mappings = data[0]["mappings"]
        self.assertEqual(mappings[0]["finding"]["title"], "B")
        self.assertEqual(mappings[1]["finding"]["title"], "A")

    def test_22_api_is_read_only(self):
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/remediation", json={})
        self.assertEqual(resp.status_code, 405)
        resp = self.client.put(f"/api/assessments/{self.assessment.id}/remediation", json={})
        self.assertEqual(resp.status_code, 405)
        resp = self.client.delete(f"/api/assessments/{self.assessment.id}/remediation")
        self.assertEqual(resp.status_code, 405)

    def test_23_existing_compliance_api_behavior_unaffected(self):
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/compliance")
        self.assertEqual(resp.status_code, 200)

    def test_24_existing_remediation_model_behavior_unaffected(self):
        g = RemediationGuidance(title="T", summary="S", detailed_guidance="D", remediation_type=RemediationType.code, priority=RemediationPriority.low, verification_guidance="V")
        self.db.add(g)
        self.db.commit()
        self.assertEqual(self.db.query(RemediationGuidance).count(), 1)

    def test_25_existing_remediation_mapping_intelligence_unaffected(self):
        f = self._create_finding(self.job.id, "F", "sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        self.assertEqual(self.db.query(FindingRemediation).count(), 1)

if __name__ == '__main__':
    unittest.main()
