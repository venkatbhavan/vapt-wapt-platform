import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity
from app.models.remediation import (
    RemediationGuidance,
    FindingRemediation,
    RemediationType,
    RemediationPriority,
    RemediationMappingConfidence
)
from app.models.compliance import ComplianceFramework, ComplianceControl, FindingComplianceMapping, MappingConfidence, MappingType
from app.models.attack_surface import Asset

class TestRemediationModels(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db = self.SessionLocal()

        # Setup base assessment data
        project = Project(name="Test Project", description="Test")
        self.db.add(project)
        self.db.flush()

        self.assessment = Assessment(name="Test Assessment", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        self.db.add(self.assessment)
        self.db.flush()

        self.scan_job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(self.scan_job)
        self.db.flush()

        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Test Finding 1",
            severity=FindingSeverity.low
        )
        self.db.add(self.finding)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_1_create_remediation_guidance(self):
        guidance = RemediationGuidance(
            title="Fix SSL",
            summary="Disable SSLv3",
            detailed_guidance="Change config to use TLS 1.2+",
            remediation_type=RemediationType.configuration,
            priority=RemediationPriority.high,
            verification_guidance="Run nmap ssl-enum-ciphers"
        )
        self.db.add(guidance)
        self.db.commit()

        g = self.db.query(RemediationGuidance).first()
        self.assertEqual(g.title, "Fix SSL")
        self.assertEqual(g.summary, "Disable SSLv3")
        self.assertEqual(g.detailed_guidance, "Change config to use TLS 1.2+")
        self.assertEqual(g.remediation_type, RemediationType.configuration)
        self.assertEqual(g.priority, RemediationPriority.high)
        self.assertEqual(g.verification_guidance, "Run nmap ssl-enum-ciphers")
        self.assertIsNotNone(g.created_at)
        self.assertIsNotNone(g.updated_at)

    def test_2_required_fields(self):
        guidance = RemediationGuidance(title="Missing Fields")
        self.db.add(guidance)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_3_enum_values_persisted(self):
        guidance = RemediationGuidance(
            title="Update Packages",
            summary="Update apt",
            detailed_guidance="apt-get update && apt-get upgrade",
            remediation_type=RemediationType.dependency,
            priority=RemediationPriority.critical,
            verification_guidance="Check dpkg -l"
        )
        self.db.add(guidance)
        self.db.commit()

        g = self.db.query(RemediationGuidance).first()
        self.assertEqual(g.remediation_type.value, "dependency")
        self.assertEqual(g.priority.value, "critical")

    def test_4_create_finding_remediation(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="Change config to use TLS 1.2+",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="Run nmap"
        )
        self.db.add(g)
        self.db.flush()

        mapping = FindingRemediation(
            finding_id=self.finding.id,
            remediation_guidance_id=g.id,
            rationale="Finding indicates SSLv3 is enabled",
            mapping_confidence=RemediationMappingConfidence.high
        )
        self.db.add(mapping)
        self.db.commit()

        m = self.db.query(FindingRemediation).first()
        self.assertEqual(m.finding_id, self.finding.id)
        self.assertEqual(m.remediation_guidance_id, g.id)
        self.assertEqual(m.mapping_confidence.value, "high")

    def test_5_6_finding_remediation_bidirectional_relationship(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="Change config to use TLS 1.2+",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="Run nmap"
        )
        self.db.add(g)
        self.db.flush()

        mapping = FindingRemediation(
            finding=self.finding,
            remediation_guidance=g,
            rationale="Finding indicates SSLv3 is enabled",
            mapping_confidence=RemediationMappingConfidence.high
        )
        self.db.add(mapping)
        self.db.commit()

        self.assertEqual(len(self.finding.remediation_mappings), 1)
        self.assertEqual(self.finding.remediation_mappings[0].remediation_guidance.title, "Fix SSL")

        self.assertEqual(len(g.finding_mappings), 1)
        self.assertEqual(g.finding_mappings[0].finding.title, "Test Finding 1")

    def test_7_multiple_remediations_for_one_finding(self):
        g1 = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        g2 = RemediationGuidance(
            title="Update OpenSSL", summary="Patch library", detailed_guidance="...",
            remediation_type=RemediationType.dependency, priority=RemediationPriority.medium, verification_guidance="..."
        )
        self.db.add_all([g1, g2])
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g1.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        m2 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g2.id, rationale="r2", mapping_confidence=RemediationMappingConfidence.medium)
        self.db.add_all([m1, m2])
        self.db.commit()

        self.assertEqual(len(self.finding.remediation_mappings), 2)

    def test_8_unique_constraint(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        m2 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r2", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add_all([m1, m2])

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_9_different_findings_same_remediation(self):
        f2 = Finding(scan_job_id=self.scan_job.id, title="Test Finding 2", severity=FindingSeverity.medium)
        self.db.add(f2)

        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        m2 = FindingRemediation(finding_id=f2.id, remediation_guidance_id=g.id, rationale="r2", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add_all([m1, m2])
        self.db.commit()

        self.assertEqual(len(g.finding_mappings), 2)

    def test_10_cascade_delete_finding(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add(m1)
        self.db.commit()

        self.db.delete(self.finding)
        self.db.commit()

        mappings = self.db.query(FindingRemediation).all()
        self.assertEqual(len(mappings), 0)

        # Guidance should still exist
        g_count = self.db.query(RemediationGuidance).count()
        self.assertEqual(g_count, 1)

    def test_11_cascade_delete_remediation(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add(m1)
        self.db.commit()

        self.db.delete(g)
        self.db.commit()

        mappings = self.db.query(FindingRemediation).all()
        self.assertEqual(len(mappings), 0)

        # Finding should still exist
        f_count = self.db.query(Finding).count()
        self.assertEqual(f_count, 1)

    def test_12_mapping_confidence_values(self):
        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.low)
        self.db.add(m1)
        self.db.commit()

        m_db = self.db.query(FindingRemediation).first()
        self.assertEqual(m_db.mapping_confidence, RemediationMappingConfidence.low)

    def test_13_assessment_isolation(self):
        f2 = Finding(scan_job_id=self.scan_job.id, title="Test Finding 2", severity=FindingSeverity.medium)
        self.db.add(f2)

        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()

        m1 = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="r1", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add(m1)
        self.db.commit()

        # The relationship Finding -> ScanJob -> Assessment isolates the remediation mapping
        self.assertEqual(m1.finding.scan_job.assessment_id, self.assessment.id)

    def test_14_existing_compliance_mappings_unaffected(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.1", title="Control 1")
        self.db.add(ctrl)
        self.db.flush()

        cmap = FindingComplianceMapping(
            finding_id=self.finding.id, control_id=ctrl.id, rationale="Comp", mapping_type=MappingType.direct, mapping_confidence=MappingConfidence.high, source="Manual"
        )
        self.db.add(cmap)

        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()
        rmap = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="Rem", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add(rmap)
        self.db.commit()

        self.assertEqual(len(self.finding.compliance_mappings), 1)
        self.assertEqual(len(self.finding.remediation_mappings), 1)

    def test_15_existing_attack_surface_unaffected(self):
        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.1", asset_type="host")
        self.db.add(asset)
        self.db.flush()

        self.finding.asset_id = asset.id

        g = RemediationGuidance(
            title="Fix SSL", summary="Disable SSLv3", detailed_guidance="...",
            remediation_type=RemediationType.configuration, priority=RemediationPriority.high, verification_guidance="..."
        )
        self.db.add(g)
        self.db.flush()
        rmap = FindingRemediation(finding_id=self.finding.id, remediation_guidance_id=g.id, rationale="Rem", mapping_confidence=RemediationMappingConfidence.high)
        self.db.add(rmap)
        self.db.commit()

        self.assertEqual(self.finding.asset_id, asset.id)
        self.assertEqual(len(self.finding.remediation_mappings), 1)

if __name__ == '__main__':
    unittest.main()
