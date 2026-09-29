import unittest
from unittest.mock import patch
from app.worker.scanners.registry import get_scanner, get_scanners
from app.worker.scanners.mock import MockScannerAdapter
from app.worker.scanners.nmap import NmapScannerAdapter
from app.worker.scanners.zap import ZapScannerAdapter
from app.worker.service import process_scan_job
from app.worker.scanners.models import ScannerError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus
import app.worker.service

class TestRegistry(unittest.TestCase):
    def test_nmap_adapter_selection(self):
        for profile in ["safe", "standard", "ports_only", "full"]:
            adapter = get_scanner(profile)
            self.assertIsInstance(adapter, NmapScannerAdapter)

    def test_zap_adapter_selection(self):
        for profile in ["passive", "active", "deep"]:
            adapter = get_scanner(profile)
            self.assertIsInstance(adapter, ZapScannerAdapter)

    def test_explicit_mock_adapter_selection_for_tests(self):
        # Demonstrates how tests explicitly inject MockScannerAdapter without registry guessing
        with patch('app.worker.service.get_scanner', return_value=MockScannerAdapter()) as mock_get:
            adapter = app.worker.service.get_scanner("any_profile")
            self.assertIsInstance(adapter, MockScannerAdapter)
            mock_get.assert_called_once_with("any_profile")

    def test_unsupported_profile_fails(self):
        with self.assertRaisesRegex(ValueError, "No appropriate scanner adapter found"):
            get_scanner("non_existent_profile")

    def test_authorization_enforced_outside_registry(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        p = Project(name="Test")
        db.add(p)
        db.flush()

        a = Assessment(project_id=p.id, name="Test", target="http://127.0.0.1", scope="Test", authorization_confirmed=False)
        db.add(a)
        db.flush()

        job = ScanJob(assessment_id=a.id, scan_profile="active")
        db.add(job)
        db.commit()

        # Try to process unauthorized active scan
        # We explicitly patch the scanner so the registry is not invoked.
        # This proves the authorization happens BEFORE any scanner is executed.
        with patch('app.worker.service.get_scanner') as mock_get_scanner:
            with self.assertRaises(ValueError):
                process_scan_job(db, job.id)
                
            # Ensure registry wasn't even called because auth blocked it
            mock_get_scanner.assert_not_called()

if __name__ == "__main__":
    unittest.main()
