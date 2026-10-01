import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding as FindingModel, FindingSeverity
from app.models.compliance import ComplianceFramework, ComplianceControl, FindingComplianceMapping, MappingType, MappingConfidence
import app.models.attack_surface
import app.models.compliance
from app.worker.compliance.mapper import map_finding_to_compliance

class TestComplianceMapping(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db = self.SessionLocal()

        project = Project(name="Test", description="Test")
        self.db.add(project)
        self.db.flush()

        self.assessment = Assessment(name="Test Assessment", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        self.db.add(self.assessment)
        self.db.flush()

        self.scan_job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(self.scan_job)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _create_finding(self, normalized_type: str) -> FindingModel:
        f = FindingModel(
            scan_job_id=self.scan_job.id,
            title=f"Test {normalized_type}",
            severity=FindingSeverity.high,
            normalized_type=normalized_type
        )
        self.db.add(f)
        self.db.commit()
        self.db.refresh(f)
        return f

    def _get_mappings(self, finding_id: int):
        return self.db.query(FindingComplianceMapping).filter_by(finding_id=finding_id).all()

    def test_01_owasp_sql_injection(self):
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        owasp = [m for m in mappings if m.control.framework.name == "OWASP Top 10"]
        self.assertEqual(len(owasp), 1)
        self.assertEqual(owasp[0].control.control_id, "A03:2021")
        self.assertEqual(owasp[0].mapping_type, MappingType.direct)
        self.assertEqual(owasp[0].mapping_confidence, MappingConfidence.high)

    def test_02_owasp_xss(self):
        f = self._create_finding("cross_site_scripting")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        owasp = [m for m in mappings if m.control.framework.name == "OWASP Top 10"]
        self.assertEqual(len(owasp), 1)
        self.assertEqual(owasp[0].control.control_id, "A03:2021")
        self.assertEqual(owasp[0].mapping_type, MappingType.direct)
        self.assertEqual(owasp[0].mapping_confidence, MappingConfidence.high)

    def test_03_owasp_missing_security_headers(self):
        f = self._create_finding("missing_security_headers")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        owasp = [m for m in mappings if m.control.framework.name == "OWASP Top 10"]
        self.assertEqual(len(owasp), 1)
        self.assertEqual(owasp[0].control.control_id, "A05:2021")
        self.assertEqual(owasp[0].mapping_type, MappingType.direct)
        self.assertEqual(owasp[0].mapping_confidence, MappingConfidence.high)

    def test_04_owasp_exposed_service(self):
        f = self._create_finding("exposed_service")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        owasp = [m for m in mappings if m.control.framework.name == "OWASP Top 10"]
        self.assertEqual(len(owasp), 1)
        self.assertEqual(owasp[0].control.control_id, "A05:2021")
        self.assertEqual(owasp[0].mapping_type, MappingType.related)
        self.assertEqual(owasp[0].mapping_confidence, MappingConfidence.medium)

    def test_05_owasp_weak_ssh_no_mapping(self):
        f = self._create_finding("weak_ssh_configuration")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        owasp = [m for m in mappings if m.control.framework.name == "OWASP Top 10"]
        self.assertEqual(len(owasp), 0)

    def test_06_nist_missing_security_headers(self):
        f = self._create_finding("missing_security_headers")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        nist = [m for m in mappings if "NIST" in m.control.framework.name]
        self.assertEqual(len(nist), 1)
        self.assertEqual(nist[0].control.control_id, "PR.PS-01")
        self.assertEqual(nist[0].mapping_type, MappingType.related)
        self.assertEqual(nist[0].mapping_confidence, MappingConfidence.medium)

    def test_07_nist_exposed_service(self):
        f = self._create_finding("exposed_service")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        nist = [m for m in mappings if "NIST" in m.control.framework.name]
        self.assertEqual(len(nist), 1)
        self.assertEqual(nist[0].control.control_id, "PR.PS-01")

    def test_08_nist_weak_ssh(self):
        f = self._create_finding("weak_ssh_configuration")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        nist = [m for m in mappings if "NIST" in m.control.framework.name]
        self.assertEqual(len(nist), 1)
        self.assertEqual(nist[0].control.control_id, "PR.PS-01")
        self.assertEqual(nist[0].mapping_type, MappingType.related)
        self.assertEqual(nist[0].mapping_confidence, MappingConfidence.medium)

    def test_09_10_nist_no_mapping_for_injections(self):
        f1 = self._create_finding("sql_injection")
        f2 = self._create_finding("cross_site_scripting")
        map_finding_to_compliance(self.db, f1)
        map_finding_to_compliance(self.db, f2)

        nist1 = [m for m in self._get_mappings(f1.id) if "NIST" in m.control.framework.name]
        nist2 = [m for m in self._get_mappings(f2.id) if "NIST" in m.control.framework.name]
        self.assertEqual(len(nist1), 0)
        self.assertEqual(len(nist2), 0)

    def test_11_unknown_normalized_type(self):
        f = self._create_finding("unknown")
        map_finding_to_compliance(self.db, f)
        self.assertEqual(len(self._get_mappings(f.id)), 0)

        f2 = self._create_finding("random_unmapped")
        map_finding_to_compliance(self.db, f2)
        self.assertEqual(len(self._get_mappings(f2.id)), 0)

    def test_12_same_mapping_twice_idempotent(self):
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)
        map_finding_to_compliance(self.db, f) # Second time

        mappings = self._get_mappings(f.id)
        self.assertEqual(len(mappings), 1)

    def test_13_14_framework_and_control_idempotent(self):
        f1 = self._create_finding("sql_injection")
        f2 = self._create_finding("cross_site_scripting") # Both map to OWASP A03

        map_finding_to_compliance(self.db, f1)
        map_finding_to_compliance(self.db, f2)

        fw_count = self.db.query(ComplianceFramework).filter_by(name="OWASP Top 10").count()
        ctrl_count = self.db.query(ComplianceControl).filter_by(control_id="A03:2021").count()

        self.assertEqual(fw_count, 1)
        self.assertEqual(ctrl_count, 1)

    def test_15_same_control_id_different_frameworks(self):
        f = self._create_finding("missing_security_headers")
        map_finding_to_compliance(self.db, f) # Maps to OWASP A05 and NIST PR.PS-01

        controls = self.db.query(ComplianceControl).all()
        # Verify it resolves them correctly
        self.assertEqual(len(controls), 2)

    def test_16_one_finding_multiple_mappings(self):
        f = self._create_finding("missing_security_headers")
        map_finding_to_compliance(self.db, f)

        mappings = self._get_mappings(f.id)
        self.assertEqual(len(mappings), 2) # OWASP and NIST

    def test_17_compliance_mapping_does_not_duplicate_finding(self):
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)

        finding_count = self.db.query(FindingModel).count()
        self.assertEqual(finding_count, 1)

    def test_19_20_21_22_mapping_traits_preserved(self):
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)

        mapping = self._get_mappings(f.id)[0]
        self.assertEqual(mapping.rationale, "SQL injection is an injection vulnerability and is directly covered by the OWASP Top 10:2021 Injection category.")
        self.assertEqual(mapping.source, "OWASP Top 10:2021 — A03:2021 Injection")
        self.assertEqual(mapping.mapping_confidence, MappingConfidence.high)
        self.assertEqual(mapping.mapping_type, MappingType.direct)

    def test_23_assessment_isolation_maintained(self):
        # Mappings are bound to the finding. Findings are bound to scanjobs, scanjobs to assessments.
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)

        mapping = self._get_mappings(f.id)[0]
        self.assertEqual(mapping.finding.scan_job.assessment.target, "127.0.0.1")

    def test_24_no_mapping_no_failure(self):
        f = self._create_finding("something_weird")
        try:
            map_finding_to_compliance(self.db, f)
        except Exception:
            self.fail("map_finding_to_compliance raised Exception unexpectedly!")

if __name__ == '__main__':
    unittest.main()
