import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.assessment import Base, Assessment, Project, Finding, ScanJob
from app.models.attack_surface import Asset
from app.models.report import Report, ReportStatus
from app.services.report_engine import generate_report_dataset, generate_report

class TestReportEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

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

        self.asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.1")
        self.db.add(self.asset)
        self.db.commit()
        
        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Open Port",
            severity="medium",
            confidence="high",
            risk_score=5.5,
            risk_level="medium",
            status="open",
            asset_id=self.asset.id,
            normalized_type="open_port",
            scanner_sources=["nmap"]
        )
        self.db.add(self.finding)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_generate_report_dataset(self):
        dataset = generate_report_dataset(self.db, self.assessment.id)
        self.assertEqual(dataset.scope.name, "Test Assessment")
        self.assertEqual(dataset.executive_summary.total_findings, 1)
        self.assertEqual(dataset.executive_summary.medium_findings, 1)
        self.assertEqual(dataset.executive_summary.total_assets, 1)
        self.assertEqual(dataset.risk_summary.severity_distribution["medium"], 1)
        self.assertEqual(len(dataset.technical_findings), 1)
        
        tf = dataset.technical_findings[0]
        self.assertEqual(tf.title, "Open Port")
        self.assertEqual(tf.severity, "medium")
        self.assertEqual(tf.scanner_sources, ["nmap"])

    def test_generate_report(self):
        report = generate_report(self.db, self.assessment.id, "Final Report")
        self.assertEqual(report.title, "Final Report")
        self.assertEqual(report.status, ReportStatus.generated)
        self.assertIsNotNone(report.generated_at)
        
        # Test snapshot
        snapshot = report.snapshot
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(snapshot["executive_summary"]["total_findings"], 1)

    def test_assessment_isolation(self):
        # Create a second assessment with findings
        a2 = Assessment(
            project_id=self.project.id,
            name="A2",
            target="10.0.0.1",
            scope="10.0.0.1"
        )
        self.db.add(a2)
        self.db.commit()
        
        sj2 = ScanJob(assessment_id=a2.id, scan_profile="standard")
        self.db.add(sj2)
        self.db.commit()
        
        f2 = Finding(scan_job_id=sj2.id, title="A2 Finding", severity="critical")
        self.db.add(f2)
        self.db.commit()
        
        dataset = generate_report_dataset(self.db, self.assessment.id)
        # Should only see finding from A1
        self.assertEqual(dataset.executive_summary.total_findings, 1)
        self.assertEqual(dataset.technical_findings[0].title, "Open Port")

    def test_empty_assessment(self):
        a_empty = Assessment(project_id=self.project.id, name="Empty", target="1.1.1.1", scope="1.1.1.1")
        self.db.add(a_empty)
        self.db.commit()
        
        dataset = generate_report_dataset(self.db, a_empty.id)
        self.assertEqual(dataset.executive_summary.total_findings, 0)
        self.assertEqual(dataset.executive_summary.total_assets, 0)
        self.assertEqual(len(dataset.technical_findings), 0)

if __name__ == '__main__':
    unittest.main()