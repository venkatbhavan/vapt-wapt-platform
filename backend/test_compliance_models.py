import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding as DbFinding, FindingSeverity
from app.models.compliance import ComplianceFramework, ComplianceControl, FindingComplianceMapping, MappingConfidence
import app.models.attack_surface # Ensure they are loaded
import app.models.compliance # Ensure they are loaded

class TestComplianceModels(unittest.TestCase):
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

        self.finding = DbFinding(
            scan_job_id=self.scan_job.id,
            title="Test Finding",
            severity=FindingSeverity.low
        )
        self.db.add(self.finding)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_1_create_framework(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.commit()

        fw_db = self.db.query(ComplianceFramework).first()
        self.assertEqual(fw_db.name, "ISO")
        self.assertEqual(fw_db.version, "27001")

    def test_2_create_control_under_framework(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.commit()

        ctrl_db = self.db.query(ComplianceControl).first()
        self.assertEqual(ctrl_db.control_id, "A.8.2")
        self.assertEqual(ctrl_db.framework_id, fw.id)

    def test_3_mapping_finding_to_control(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.flush()

        mapping = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.high,
            source="Manual"
        )
        self.db.add(mapping)
        self.db.commit()

        map_db = self.db.query(FindingComplianceMapping).first()
        self.assertEqual(map_db.finding_id, self.finding.id)
        self.assertEqual(map_db.control_id, ctrl.id)
        self.assertEqual(map_db.mapping_confidence, MappingConfidence.high)
        self.assertEqual(map_db.mapping_confidence.value, "high")

    def test_4_5_framework_controls_relationships(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.commit()

        fw_db = self.db.query(ComplianceFramework).first()
        self.assertEqual(len(fw_db.controls), 1)
        self.assertEqual(fw_db.controls[0].control_id, "A.8.2")

        ctrl_db = self.db.query(ComplianceControl).first()
        self.assertEqual(ctrl_db.framework.name, "ISO")

    def test_6_7_8_mapping_relationships(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.flush()

        mapping = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.low,
            source="System"
        )
        self.db.add(mapping)
        self.db.commit()

        self.db.refresh(self.finding)
        self.assertEqual(len(self.finding.compliance_mappings), 1)

        m_db = self.db.query(FindingComplianceMapping).first()
        self.assertEqual(m_db.finding.title, "Test Finding")
        self.assertEqual(m_db.control.title, "Testing")

        c_db = self.db.query(ComplianceControl).first()
        self.assertEqual(len(c_db.mappings), 1)

    def test_9_duplicate_framework_rejected(self):
        fw1 = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw1)
        self.db.commit()

        fw2 = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw2)

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_10_duplicate_control_rejected(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        c1 = ComplianceControl(framework_id=fw.id, control_id="A.8", title="Testing")
        self.db.add(c1)
        self.db.commit()

        c2 = ComplianceControl(framework_id=fw.id, control_id="A.8", title="Testing2")
        self.db.add(c2)

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_11_same_control_id_different_frameworks(self):
        fw1 = ComplianceFramework(name="ISO", version="27001")
        fw2 = ComplianceFramework(name="NIST", version="2.0")
        self.db.add(fw1)
        self.db.add(fw2)
        self.db.flush()

        c1 = ComplianceControl(framework_id=fw1.id, control_id="1.1", title="Testing")
        c2 = ComplianceControl(framework_id=fw2.id, control_id="1.1", title="Testing")
        self.db.add(c1)
        self.db.add(c2)
        self.db.commit()

        self.assertEqual(self.db.query(ComplianceControl).count(), 2)

    def test_12_duplicate_mapping_rejected(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.flush()

        m1 = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.low,
            source="System"
        )
        self.db.add(m1)
        self.db.commit()

        m2 = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.low,
            source="System"
        )
        self.db.add(m2)

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_13_deleting_framework_cascades(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.flush()

        m1 = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.low,
            source="System"
        )
        self.db.add(m1)
        self.db.commit()

        self.db.delete(fw)
        self.db.commit()

        self.assertEqual(self.db.query(ComplianceFramework).count(), 0)
        self.assertEqual(self.db.query(ComplianceControl).count(), 0)
        self.assertEqual(self.db.query(FindingComplianceMapping).count(), 0)

    def test_14_deleting_finding_cascades(self):
        fw = ComplianceFramework(name="ISO", version="27001")
        self.db.add(fw)
        self.db.flush()

        ctrl = ComplianceControl(framework_id=fw.id, control_id="A.8.2", title="Testing")
        self.db.add(ctrl)
        self.db.flush()

        m1 = FindingComplianceMapping(mapping_type="direct",
            finding_id=self.finding.id,
            control_id=ctrl.id,
            rationale="Because",
            mapping_confidence=MappingConfidence.low,
            source="System"
        )
        self.db.add(m1)
        self.db.commit()

        self.db.delete(self.finding)
        self.db.commit()

        self.assertEqual(self.db.query(DbFinding).count(), 0)
        self.assertEqual(self.db.query(ComplianceFramework).count(), 1)
        self.assertEqual(self.db.query(ComplianceControl).count(), 1)
        self.assertEqual(self.db.query(FindingComplianceMapping).count(), 0)

    def test_15_existing_finding_behavior_intact(self):
        self.assertEqual(self.finding.severity, FindingSeverity.low)
        self.assertEqual(self.finding.title, "Test Finding")

    def test_16_assessment_isolation_preserved(self):
        self.assertEqual(self.finding.scan_job.assessment.target, "127.0.0.1")

    def test_17_finding_can_exist_without_mapping(self):
        self.assertEqual(len(self.finding.compliance_mappings), 0)

if __name__ == '__main__':
    unittest.main()
