import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding as FindingModel, FindingSeverity, FindingStatus
from app.models.compliance import ComplianceFramework, ComplianceControl, FindingComplianceMapping, MappingType, MappingConfidence

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
client = TestClient(app)

class TestComplianceAPI(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        project = Project(name="Test Project API", description="Test")
        self.db.add(project)
        self.db.flush()
        
        self.assessment_a = Assessment(name="Assessment A", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        self.assessment_b = Assessment(name="Assessment B", project_id=project.id, target="127.0.0.2", scope="local", authorization_confirmed=True)
        self.db.add_all([self.assessment_a, self.assessment_b])
        self.db.flush()

        self.scan_job_a = ScanJob(assessment_id=self.assessment_a.id, scan_profile="standard")
        self.scan_job_b = ScanJob(assessment_id=self.assessment_b.id, scan_profile="standard")
        self.db.add_all([self.scan_job_a, self.scan_job_b])
        self.db.commit()

    def tearDown(self):
        # Clean up created tables
        Base.metadata.drop_all(bind=engine)
        self.db.close()

    def _create_mapping(self, finding, fw_name="OWASP", fw_version="2021", control_id="A01", control_title="Broken Access Control"):
        fw = self.db.query(ComplianceFramework).filter_by(name=fw_name, version=fw_version).first()
        if not fw:
            fw = ComplianceFramework(name=fw_name, version=fw_version)
            self.db.add(fw)
            self.db.flush()
        
        ctrl = self.db.query(ComplianceControl).filter_by(framework_id=fw.id, control_id=control_id).first()
        if not ctrl:
            ctrl = ComplianceControl(framework_id=fw.id, control_id=control_id, title=control_title)
            self.db.add(ctrl)
            self.db.flush()
            
        mapping = FindingComplianceMapping(
            finding_id=finding.id,
            control_id=ctrl.id,
            rationale="Test rationale",
            mapping_type=MappingType.direct,
            mapping_confidence=MappingConfidence.high,
            source="Test source"
        )
        self.db.add(mapping)
        self.db.commit()
        return fw, ctrl, mapping

    def test_01_existing_assessment_no_mappings_returns_empty_frameworks(self):
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["assessment_id"], self.assessment_a.id)
        self.assertEqual(data["frameworks"], [])

    def test_02_nonexistent_assessment_returns_404(self):
        response = client.get("/api/assessments/99999/compliance")
        self.assertEqual(response.status_code, 404)

    def test_03_one_framework_control_mapping(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="Test Finding", severity=FindingSeverity.high, status=FindingStatus.open)
        self.db.add(f)
        self.db.commit()
        
        self._create_mapping(f)
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data["frameworks"]), 1)
        fw = data["frameworks"][0]
        self.assertEqual(fw["name"], "OWASP")
        
        self.assertEqual(len(fw["controls"]), 1)
        ctrl = fw["controls"][0]
        self.assertEqual(ctrl["control_id"], "A01")
        
        self.assertEqual(len(ctrl["mappings"]), 1)
        mapping = ctrl["mappings"][0]
        
        # 4. Mapping fields preserved
        self.assertEqual(mapping["mapping_type"], "direct")
        self.assertEqual(mapping["mapping_confidence"], "high")
        self.assertEqual(mapping["rationale"], "Test rationale")
        self.assertEqual(mapping["source"], "Test source")
        
        # 5. Finding fields returned correctly
        self.assertEqual(mapping["finding_id"], f.id)
        self.assertEqual(mapping["finding_title"], "Test Finding")
        self.assertEqual(mapping["finding_severity"], "high")
        self.assertEqual(mapping["finding_status"], "open")

    def test_06_multiple_findings_mapped_to_same_control(self):
        f1 = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        f2 = FindingModel(scan_job_id=self.scan_job_a.id, title="F2", severity=FindingSeverity.medium)
        self.db.add_all([f1, f2])
        self.db.commit()
        
        self._create_mapping(f1)
        self._create_mapping(f2)
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        
        controls = data["frameworks"][0]["controls"]
        self.assertEqual(len(controls), 1)
        mappings = controls[0]["mappings"]
        self.assertEqual(len(mappings), 2)
        finding_titles = [m["finding_title"] for m in mappings]
        self.assertIn("F1", finding_titles)
        self.assertIn("F2", finding_titles)

    def test_07_one_finding_mapped_to_multiple_controls(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        self.db.add(f)
        self.db.commit()
        
        self._create_mapping(f, control_id="A01")
        self._create_mapping(f, control_id="A02")
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        
        controls = data["frameworks"][0]["controls"]
        self.assertEqual(len(controls), 2)
        
        for c in controls:
            self.assertEqual(len(c["mappings"]), 1)
            self.assertEqual(c["mappings"][0]["finding_title"], "F1")

    def test_08_one_finding_mapped_to_multiple_frameworks(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        self.db.add(f)
        self.db.commit()
        
        self._create_mapping(f, fw_name="FW1")
        self._create_mapping(f, fw_name="FW2")
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        
        self.assertEqual(len(data["frameworks"]), 2)

    def test_09_assessment_isolation(self):
        f_a = FindingModel(scan_job_id=self.scan_job_a.id, title="Finding A", severity=FindingSeverity.low)
        f_b = FindingModel(scan_job_id=self.scan_job_b.id, title="Finding B", severity=FindingSeverity.low)
        self.db.add_all([f_a, f_b])
        self.db.commit()
        
        # Both mapped to same framework/control for complication
        self._create_mapping(f_a, fw_name="Shared", control_id="C1")
        self._create_mapping(f_b, fw_name="Shared", control_id="C1")
        
        response_a = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data_a = response_a.json()
        
        # Assessment A should ONLY see Finding A
        mappings_a = data_a["frameworks"][0]["controls"][0]["mappings"]
        self.assertEqual(len(mappings_a), 1)
        self.assertEqual(mappings_a[0]["finding_title"], "Finding A")
        
        # Assessment B should ONLY see Finding B
        response_b = client.get(f"/api/assessments/{self.assessment_b.id}/compliance")
        data_b = response_b.json()
        mappings_b = data_b["frameworks"][0]["controls"][0]["mappings"]
        self.assertEqual(len(mappings_b), 1)
        self.assertEqual(mappings_b[0]["finding_title"], "Finding B")

    def test_10_11_controls_and_frameworks_with_no_mappings_excluded(self):
        # Create an orphaned framework and control that has mappings, but NOT for this assessment
        f_b = FindingModel(scan_job_id=self.scan_job_b.id, title="Finding B", severity=FindingSeverity.low)
        self.db.add(f_b)
        self.db.commit()
        self._create_mapping(f_b, fw_name="Ghost", control_id="C99")
        
        response_a = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data_a = response_a.json()
        self.assertEqual(len(data_a["frameworks"]), 0) # Ghost framework should not appear

    def test_12_multiple_mappings_do_not_produce_duplicate_mapping_objects(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        self.db.add(f)
        self.db.commit()
        
        # Create mapping normally
        self._create_mapping(f, control_id="A01")
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        mappings = data["frameworks"][0]["controls"][0]["mappings"]
        self.assertEqual(len(mappings), 1)
        
    def test_13_ordering_is_deterministic(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        self.db.add(f)
        self.db.commit()
        
        # Insert out of order
        self._create_mapping(f, fw_name="Z", fw_version="2", control_id="99")
        self._create_mapping(f, fw_name="A", fw_version="1", control_id="11")
        self._create_mapping(f, fw_name="A", fw_version="1", control_id="01")
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        
        self.assertEqual(data["frameworks"][0]["name"], "A")
        self.assertEqual(data["frameworks"][1]["name"], "Z")
        self.assertEqual(data["frameworks"][0]["controls"][0]["control_id"], "01")
        self.assertEqual(data["frameworks"][0]["controls"][1]["control_id"], "11")

    def test_14_raw_evidence_not_exposed(self):
        f = FindingModel(scan_job_id=self.scan_job_a.id, title="F1", severity=FindingSeverity.low)
        self.db.add(f)
        self.db.commit()
        self._create_mapping(f)
        
        response = client.get(f"/api/assessments/{self.assessment_a.id}/compliance")
        data = response.json()
        mapping_str = str(data)
        self.assertNotIn("evidence", mapping_str.lower())

if __name__ == '__main__':
    unittest.main()
