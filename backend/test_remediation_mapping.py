import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding as FindingModel, FindingSeverity, Evidence, EvidenceType
from app.models.remediation import RemediationGuidance, FindingRemediation, RemediationType, RemediationPriority, RemediationMappingConfidence
from app.models.compliance import FindingComplianceMapping, ComplianceFramework, ComplianceControl, MappingType, MappingConfidence
import app.models.attack_surface
import app.models.compliance
import app.models.remediation
from app.worker.remediation.mapper import map_finding_to_remediation
from app.worker.compliance.mapper import map_finding_to_compliance
from app.worker.remediation.catalog import REMEDIATION_CATALOG

class TestRemediationMapping(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
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
        self.engine.dispose()

    def _create_finding(self, normalized_type: str, scan_job_id: int = None) -> FindingModel:
        f = FindingModel(
            scan_job_id=scan_job_id or self.scan_job.id,
            title=f"Test {normalized_type}",
            severity=FindingSeverity.high,
            normalized_type=normalized_type
        )
        self.db.add(f)
        self.db.commit()
        self.db.refresh(f)
        return f

    def _get_mappings(self, finding_id: int):
        return self.db.query(FindingRemediation).filter_by(finding_id=finding_id).all()

    def test_01_all_approved_types_have_remediation(self):
        approved_types = [
            "missing_security_headers", "exposed_service",
            "sql_injection", "cross_site_scripting", "weak_ssh_configuration"
        ]
        for nt in approved_types:
            f = self._create_finding(nt)
            map_finding_to_remediation(self.db, f)
            mappings = self._get_mappings(f.id)
            self.assertEqual(len(mappings), 1)

    def test_02_missing_security_headers_mapping(self):
        f = self._create_finding("missing_security_headers")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.title, "Configure HTTP Security Headers")
        self.assertEqual(m.remediation_guidance.remediation_type, RemediationType.configuration)
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.high)

    def test_03_exposed_service_mapping(self):
        f = self._create_finding("exposed_service")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.title, "Restrict or Disable Unnecessary Network Service")
        self.assertEqual(m.remediation_guidance.remediation_type, RemediationType.network)
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.medium)

    def test_04_sql_injection_mapping(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.title, "Use Parameterized Database Queries")
        self.assertEqual(m.remediation_guidance.remediation_type, RemediationType.code)
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.critical)

    def test_05_cross_site_scripting_mapping(self):
        f = self._create_finding("cross_site_scripting")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.title, "Implement Context-Aware Output Encoding")
        self.assertEqual(m.remediation_guidance.remediation_type, RemediationType.code)
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.high)

    def test_06_weak_ssh_configuration_mapping(self):
        f = self._create_finding("weak_ssh_configuration")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.title, "Harden SSH Configuration")
        self.assertEqual(m.remediation_guidance.remediation_type, RemediationType.configuration)
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.high)

    def test_07_unknown_produces_no_mapping(self):
        f = self._create_finding("unknown")
        map_finding_to_remediation(self.db, f)
        self.assertEqual(len(self._get_mappings(f.id)), 0)

    def test_08_unknown_does_not_create_guidance(self):
        f = self._create_finding("unknown")
        map_finding_to_remediation(self.db, f)
        self.assertEqual(self.db.query(RemediationGuidance).count(), 0)

    def test_09_exact_matching_enforced(self):
        f = self._create_finding("sql_injection ")
        map_finding_to_remediation(self.db, f)
        self.assertEqual(len(self._get_mappings(f.id)), 0)

    def test_10_similar_unrecognized_strings_no_mapping(self):
        f = self._create_finding("sql_injection_blind")
        map_finding_to_remediation(self.db, f)
        self.assertEqual(len(self._get_mappings(f.id)), 0)

    def test_11_remediation_guidance_reused(self):
        f1 = self._create_finding("sql_injection")
        f2 = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f1)
        self.db.commit()
        map_finding_to_remediation(self.db, f2)
        self.db.commit()
        self.assertEqual(self.db.query(RemediationGuidance).count(), 1)

    def test_12_finding_remediation_idempotent(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        self.assertEqual(len(self._get_mappings(f.id)), 1)

    def test_13_reprocessing_creates_no_duplicate(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        self.assertEqual(self.db.query(FindingRemediation).count(), 1)

    def test_14_multiple_findings_use_same_guidance(self):
        f1 = self._create_finding("sql_injection")
        f2 = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f2)
        self.db.commit()
        self.assertEqual(self.db.query(RemediationGuidance).count(), 1)
        self.assertEqual(self.db.query(FindingRemediation).count(), 2)

    def test_15_mapping_confidence_preserved(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.mapping_confidence, RemediationMappingConfidence.high)

    def test_16_rationale_preserved(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.rationale, "The finding indicates that untrusted input can influence database query execution.")

    def test_17_priority_preserved(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.remediation_guidance.priority, RemediationPriority.critical)

    def test_18_verification_guidance_preserved(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertIn("confirm that the previously observed injection behavior", m.remediation_guidance.verification_guidance)

    def test_19_assessment_isolation(self):
        a2 = Assessment(name="Assessment 2", project_id=self.assessment.project_id, target="10.0.0.1", scope="local", authorization_confirmed=True)
        self.db.add(a2)
        self.db.flush()
        sj2 = ScanJob(assessment_id=a2.id, scan_profile="standard")
        self.db.add(sj2)
        self.db.flush()
        f = self._create_finding("sql_injection", sj2.id)
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.finding.scan_job.assessment_id, a2.id)

    def test_20_scan_job_isolation(self):
        sj2 = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(sj2)
        self.db.flush()
        f = self._create_finding("sql_injection", sj2.id)
        map_finding_to_remediation(self.db, f)
        m = self._get_mappings(f.id)[0]
        self.assertEqual(m.finding.scan_job_id, sj2.id)

    def test_21_duplicate_findings_use_existing_id(self):
        f1 = self._create_finding("sql_injection")
        # In actual deduplication, it re-returns f1. We simulate reprocessing f1.
        map_finding_to_remediation(self.db, f1)
        map_finding_to_remediation(self.db, f1)
        self.assertEqual(len(self._get_mappings(f1.id)), 1)
        self.assertEqual(self.db.query(FindingModel).count(), 1)

    def test_22_existing_evidence_intact(self):
        f = self._create_finding("sql_injection")
        ev = Evidence(finding_id=f.id, evidence_type=EvidenceType.text, title="T", content="C", source="S")
        self.db.add(ev)
        self.db.commit()
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        self.assertEqual(len(f.evidence_list), 1)

    def test_23_existing_compliance_mappings_intact(self):
        f = self._create_finding("sql_injection")
        map_finding_to_compliance(self.db, f)
        self.db.commit()
        map_finding_to_remediation(self.db, f)
        self.db.commit()
        self.assertTrue(len(f.compliance_mappings) > 0)
        self.assertTrue(len(f.remediation_mappings) > 0)

    def test_24_mapper_does_not_commit(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        # Should not have committed, so a rollback wipes it
        self.db.rollback()
        self.assertEqual(self.db.query(FindingRemediation).count(), 0)

    def test_25_mapper_works_with_outer_transaction(self):
        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.commit() # Outer transaction commits
        self.assertEqual(self.db.query(FindingRemediation).count(), 1)

    def test_26_mapper_records_rollback(self):
        # Insert a prior reusable guidance
        g = RemediationGuidance(title="Test", summary="S", detailed_guidance="D", remediation_type=RemediationType.configuration, priority=RemediationPriority.low, verification_guidance="V")
        self.db.add(g)
        self.db.commit()

        f = self._create_finding("sql_injection")
        map_finding_to_remediation(self.db, f)
        self.db.rollback() # Simulated failure

        # Mapping should be gone
        self.assertEqual(self.db.query(FindingRemediation).count(), 0)
        # The new guidance from sql_injection should be gone
        self.assertEqual(self.db.query(RemediationGuidance).filter_by(title="Use Parameterized Database Queries").count(), 0)
        # The previously committed guidance should remain
        self.assertEqual(self.db.query(RemediationGuidance).count(), 1)


if __name__ == '__main__':
    unittest.main()
