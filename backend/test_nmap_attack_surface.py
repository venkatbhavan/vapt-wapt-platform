import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus
from app.models.attack_surface import Asset, NetworkService
from app.worker.scanners.models import ScannerResult, HostObservation, ServiceObservation, Finding
from app.worker.service import process_scan_job

class TestNmapAttackSurfaceIngestionExhaustive(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        self.project = Project(name="Ingestion Test Project")
        self.db.add(self.project)
        self.db.flush()

        self.assessment = Assessment(
            project_id=self.project.id,
            name="Assessment A",
            target="10.0.0.1",
            scope="10.0.0.1",
            authorization_confirmed=True
        )
        self.db.add(self.assessment)
        
        self.assessment_b = Assessment(
            project_id=self.project.id,
            name="Assessment B",
            target="10.0.0.1",
            scope="10.0.0.1",
            authorization_confirmed=True
        )
        self.db.add(self.assessment_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_one_host_creates_one_asset(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1")]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        assets = self.db.query(Asset).filter_by(assessment_id=self.assessment.id).all()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].ip_address, "10.0.0.1")

    def test_02_multiple_tcp_services(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[
                    ServiceObservation(port=80, protocol="tcp", state="open"),
                    ServiceObservation(port=443, protocol="tcp", state="open")
                ]
            )]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        services = self.db.query(NetworkService).all()
        self.assertEqual(len(services), 2)
        ports = {s.port for s in services}
        self.assertEqual(ports, {80, 443})

    def test_03_hostname_preserved(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1", hostname="test.local")]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        asset = self.db.query(Asset).first()
        self.assertEqual(asset.hostname, "test.local")

    def test_04_os_preserved(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1", os="Linux 2.6")]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        asset = self.db.query(Asset).first()
        self.assertEqual(asset.os, "Linux 2.6")

    def test_05_service_metadata_preserved(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[ServiceObservation(port=80, protocol="tcp", state="open", service_name="http", service_product="Apache", service_version="2.4", extra_info="(Ubuntu)")]
            )]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        svc = self.db.query(NetworkService).first()
        self.assertEqual(svc.service_name, "http")
        self.assertEqual(svc.service_product, "Apache")
        self.assertEqual(svc.service_version, "2.4")
        self.assertEqual(svc.extra_info, "(Ubuntu)")

    def test_06_tcp_and_udp_distinguished(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[
                    ServiceObservation(port=53, protocol="tcp", state="open"),
                    ServiceObservation(port=53, protocol="udp", state="open")
                ]
            )]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        services = self.db.query(NetworkService).all()
        self.assertEqual(len(services), 2)
        protocols = {s.protocol for s in services}
        self.assertEqual(protocols, {"tcp", "udp"})

    def test_07_idempotency_on_identical_reingestion(self):
        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1", hostname="test.local",
                services=[ServiceObservation(port=80, protocol="tcp", state="open", service_name="http")]
            )]
        )
        
        for i in range(2):
            job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
            self.db.add(job)
            self.db.commit()

            with patch("app.worker.service.get_scanner") as mock:
                mock.return_value.scan.return_value = res
                process_scan_job(self.db, job.id)

        assets = self.db.query(Asset).all()
        services = self.db.query(NetworkService).all()
        self.assertEqual(len(assets), 1)
        self.assertEqual(len(services), 1)

    def test_08_later_scan_adds_new_service(self):
        res1 = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1", services=[ServiceObservation(port=80, protocol="tcp", state="open")])]
        )
        res2 = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1", services=[
                ServiceObservation(port=80, protocol="tcp", state="open"),
                ServiceObservation(port=443, protocol="tcp", state="open")
            ])]
        )
        
        for res in [res1, res2]:
            job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
            self.db.add(job)
            self.db.commit()

            with patch("app.worker.service.get_scanner") as mock:
                mock.return_value.scan.return_value = res
                process_scan_job(self.db, job.id)

        services = self.db.query(NetworkService).all()
        self.assertEqual(len(services), 2)

    def test_09_later_scan_updates_metadata(self):
        res1 = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[ServiceObservation(port=80, protocol="tcp", state="open", service_name="http", service_product="Apache", service_version=None)]
            )]
        )
        res2 = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[ServiceObservation(port=80, protocol="tcp", state="open", service_name="http", service_product="Apache", service_version="2.4.x")]
            )]
        )
        
        for res in [res1, res2]:
            job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
            self.db.add(job)
            self.db.commit()

            with patch("app.worker.service.get_scanner") as mock:
                mock.return_value.scan.return_value = res
                process_scan_job(self.db, job.id)

        services = self.db.query(NetworkService).all()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].service_version, "2.4.x")

    def test_10_findings_persisted_and_risk_calculated(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            findings=[Finding(title="Open Port 80", severity="high", description="Desc", confidence="high")],
            hosts=[HostObservation(ip_address="10.0.0.1")]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        from app.models.assessment import Finding as DbFinding
        findings = self.db.query(DbFinding).all()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "high")
        self.assertIsNotNone(findings[0].risk_score)

    def test_11_assessment_isolation(self):
        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="10.0.0.1")]
        )
        
        for assess in [self.assessment, self.assessment_b]:
            job = ScanJob(assessment_id=assess.id, scan_profile="standard")
            self.db.add(job)
            self.db.commit()

            with patch("app.worker.service.get_scanner") as mock:
                mock.return_value.scan.return_value = res
                process_scan_job(self.db, job.id)

        assets = self.db.query(Asset).all()
        self.assertEqual(len(assets), 2)
        asset_assessments = {a.assessment_id for a in assets}
        self.assertEqual(asset_assessments, {self.assessment.id, self.assessment_b.id})

    def test_12_cascade_deletion(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            hosts=[HostObservation(
                ip_address="10.0.0.1",
                services=[ServiceObservation(port=80, protocol="tcp", state="open")]
            )]
        )
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        self.assertEqual(self.db.query(Asset).count(), 1)
        self.assertEqual(self.db.query(NetworkService).count(), 1)

        self.db.delete(self.assessment)
        self.db.commit()

        self.assertEqual(self.db.query(Asset).count(), 0)
        self.assertEqual(self.db.query(NetworkService).count(), 0)

    def test_transaction_rollback_on_failure(self):
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        # Normal mock result
        res = ScannerResult(
            scanner="nmap", target="10.0.0.1", scan_profile="standard",
            findings=[Finding(title="Should Rollback", severity="info", description="Desc")],
            hosts=[HostObservation(ip_address="10.0.0.1")]
        )
        
        with patch("app.worker.service.get_scanner") as mock_get_scanner:
            mock_scanner = mock_get_scanner.return_value
            mock_scanner.scan.return_value = res
            
            # Force an exception right in the middle of ingestion by mocking db.add to fail
            with patch.object(self.db, 'add', side_effect=Exception("Database crash")):
                completed_job = process_scan_job(self.db, job.id)
                
        self.assertEqual(completed_job.status, ScanJobStatus.failed)
        self.assertIn("Scanner error: Database crash", completed_job.error_message)
        
        # Verify transaction was rolled back (no findings or assets should exist)
        from app.models.assessment import Finding as DbFinding
        self.assertEqual(self.db.query(DbFinding).filter_by(scan_job_id=job.id).count(), 0)
        self.assertEqual(self.db.query(Asset).count(), 0)


if __name__ == "__main__":
    unittest.main()
