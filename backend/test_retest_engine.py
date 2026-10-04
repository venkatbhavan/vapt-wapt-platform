import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity
from app.models.retest import RetestRequest, RetestResult, RetestStatus, RetestResultStatus, RetestConfidence
from app.services.retest_engine import run_retest
from app.worker.scanners.models import ScannerResult, Finding as ScannerFinding, EvidenceItem

class TestRetestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()

        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()

        self.assessment = Assessment(
            project_id=self.project.id,
            name="Test Assessment",
            target="192.168.1.1",
            scan_profile="standard",
            status="running",
            authorization_confirmed=True,
            scope="external"
        )
        self.db.add(self.assessment)
        self.db.commit()

        self.scan_job = ScanJob(
            assessment_id=self.assessment.id,
            scan_profile="standard",
            active_scan_confirmed=True,
            status="completed"
        )
        self.db.add(self.scan_job)
        self.db.commit()
        
        from app.models.attack_surface import Asset
        self.asset = Asset(
            assessment_id=self.assessment.id,
            ip_address="192.168.1.1"
        )
        self.db.add(self.asset)
        self.db.commit()

        # Original finding
        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            asset_id=self.asset.id,
            title="Open Port 80",
            severity=FindingSeverity.medium,
            normalized_type="exposed_service",
            location="192.168.1.1:80/tcp",
            identity_hash="hash123",
            scanner_sources=["nmap"],
            confidence="high"
        )
        self.db.add(self.finding)
        self.db.commit()

        self.retest_request = RetestRequest(
            finding_id=self.finding.id,
            status=RetestStatus.requested
        )
        self.db.add(self.retest_request)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    @patch('app.services.retest_engine.get_scanner')
    @patch('app.services.retest_engine.compute_identity_hash')
    def test_retest_still_present(self, mock_compute, mock_get_scanner):
        # Setup mock compute to return exact same hash
        mock_compute.return_value = "hash123"
        
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        mock_result = ScannerResult(
            scanner="nmap",
            target="192.168.1.1",
            scan_profile="standard",
            findings=[
                ScannerFinding(
                    title="Open Port 80",
                    severity="medium",
                    description="Port is open",
                    location="192.168.1.1:80"
                )
            ]
        )
        mock_scanner.scan.return_value = mock_result
        
        updated_request = run_retest(self.db, self.retest_request.id)
        
        # Verify scanner was called with isolated context
        mock_scanner.scan.assert_called_once_with(target="192.168.1.1", scan_profile="standard")
        
        self.assertEqual(updated_request.status, RetestStatus.completed)
        self.assertIsNotNone(updated_request.completed_at)
        
        res = updated_request.result
        self.assertEqual(res.result, RetestResultStatus.still_present)
        self.assertEqual(res.previous_finding_id, self.finding.id)
        self.assertEqual(res.current_finding_id, self.finding.id)

    @patch('app.services.retest_engine.get_scanner')
    @patch('app.services.retest_engine.compute_identity_hash')
    def test_retest_fixed(self, mock_compute, mock_get_scanner):
        mock_compute.return_value = "hash_different"
        
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        # Scanner returns NO findings, or unrelated findings
        mock_result = ScannerResult(
            scanner="nmap",
            target="192.168.1.1",
            scan_profile="standard",
            findings=[]
        )
        mock_scanner.scan.return_value = mock_result
        
        updated_request = run_retest(self.db, self.retest_request.id)
        
        self.assertEqual(updated_request.status, RetestStatus.completed)
        res = updated_request.result
        self.assertEqual(res.result, RetestResultStatus.fixed)
        self.assertEqual(res.previous_finding_id, self.finding.id)
        self.assertIsNone(res.current_finding_id)

    @patch('app.services.retest_engine.get_scanner')
    @patch('app.services.retest_engine.compute_identity_hash')
    def test_retest_changed(self, mock_compute, mock_get_scanner):
        mock_compute.return_value = "hash_different"
        
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        # Return a finding that normalizes to the same type, but identity_hash differs
        mock_result = ScannerResult(
            scanner="nmap",
            target="192.168.1.1",
            scan_profile="standard",
            findings=[
                ScannerFinding(
                    title="Open Port 81",
                    severity="high",
                    description="Port moved",
                    location="192.168.1.1:81/tcp", evidence=[EvidenceItem(evidence_type="text", title="Changed Proof", content="x", source="nmap")]
                )
            ]
        )
        mock_scanner.scan.return_value = mock_result
        
        # Need to mock the normalizer so it returns the exact same normalized_type 
        with patch('app.services.retest_engine.normalize_finding') as mock_norm:
            mock_norm.return_value = {
                "normalized_type": "exposed_service",
                "normalized_category": "network_exposure",
                "root_cause": "insecure_configuration",
                "exploitability_context": None,
                "impact": "network_exposure",
                "remediation": "Fix it",
                "evidence_quality": "high",
                "confidence": "high"
            }
            
            updated_request = run_retest(self.db, self.retest_request.id)
        
        self.assertEqual(updated_request.status, RetestStatus.completed)
        res = updated_request.result
        self.assertEqual(res.result, RetestResultStatus.changed)
        self.assertEqual(len(res.evidence), 1)
        self.assertEqual(res.evidence[0].title, "Changed Proof")
        
        # Current finding should be the newly created finding
        self.assertIsNotNone(res.current_finding_id)
        self.assertNotEqual(res.current_finding_id, self.finding.id)
        
        # Verify the new finding was persisted correctly
        new_finding = self.db.query(Finding).filter(Finding.id == res.current_finding_id).first()
        self.assertEqual(new_finding.title, "Open Port 81")
        self.assertEqual(new_finding.severity, FindingSeverity.high)
        self.assertEqual(new_finding.normalized_type, "exposed_service")

    @patch('app.services.retest_engine.get_scanner')
    def test_retest_scanner_failure(self, mock_get_scanner):
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        mock_scanner.scan.side_effect = Exception("Network timeout")
        
        updated_request = run_retest(self.db, self.retest_request.id)
        
        # Request should be failed, outcome inconclusive
        self.assertEqual(updated_request.status, RetestStatus.failed)
        res = updated_request.result
        self.assertEqual(res.result, RetestResultStatus.inconclusive)
        self.assertIsNone(res.current_finding_id)
        
    @patch('app.services.retest_engine.get_scanner')
    def test_retest_null_result_failure(self, mock_get_scanner):
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        # Simulating scanner returns None or weird object
        mock_scanner.scan.return_value = None
        
        updated_request = run_retest(self.db, self.retest_request.id)
        self.assertEqual(updated_request.status, RetestStatus.failed)
        self.assertEqual(updated_request.result.result, RetestResultStatus.inconclusive)

    def test_authorization_check(self):
        # Unauthorize assessment
        self.assessment.authorization_confirmed = False
        self.db.commit()
        
        with self.assertRaises(ValueError) as context:
            run_retest(self.db, self.retest_request.id)
            
        self.assertIn("authorization not confirmed", str(context.exception).lower())
        
    @patch('app.services.retest_engine.get_scanner')
    @patch('app.services.retest_engine.compute_identity_hash')
    def test_multiple_retests(self, mock_compute, mock_get_scanner):
        mock_compute.return_value = "hash123"
        mock_scanner = MagicMock()
        mock_get_scanner.return_value = mock_scanner
        
        mock_result = ScannerResult(
            scanner="nmap", target="192.168.1.1", scan_profile="standard",
            findings=[ScannerFinding(title="P", severity="low", description="D", location="192.168.1.1:80/tcp")]
        )
        mock_scanner.scan.return_value = mock_result
        
        # 1st request
        run_retest(self.db, self.retest_request.id)
        
        # 2nd request
        req2 = RetestRequest(finding_id=self.finding.id, status=RetestStatus.requested)
        self.db.add(req2)
        self.db.commit()
        
        mock_compute.return_value = "hash_different"
        mock_result.findings = [] # simulate fixed on second run
        
        run_retest(self.db, req2.id)
        
        self.assertEqual(self.retest_request.result.result, RetestResultStatus.still_present)
        self.assertEqual(req2.result.result, RetestResultStatus.fixed)

if __name__ == '__main__':
    unittest.main()
