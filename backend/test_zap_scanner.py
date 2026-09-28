import unittest
import json
from unittest.mock import patch, MagicMock
import subprocess
from app.worker.scanners.zap import ZapScannerAdapter
from app.worker.scanners.zap_config import (
    ZapScanConfiguration, build_zap_command, ZapScanType, get_zap_config_for_profile
)
from app.worker.scanners.models import ScannerError
from app.worker.scanners.zap_parser import parse_zap_json, map_severity, map_confidence, redact_secrets

from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus
from app.worker.service import process_scan_job
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestZapScanner(unittest.TestCase):
    def setUp(self):
        self.adapter = ZapScannerAdapter()

    # Requirements 1 & 2: shell=False and Target is exactly one argument
    @patch("subprocess.run")
    def test_target_argument_safety(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        target = "http://127.0.0.1;echo-test"
        self.adapter.scan(target, "passive")
        
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        
        # Requirement 1
        self.assertEqual(kwargs.get("shell"), False)
        # Requirement 2
        self.assertIn(target, cmd)
        self.assertEqual(cmd[cmd.index("-quickurl") + 1], target)

    # Requirement 3: No arbitrary command line injection
    def test_no_arbitrary_flags(self):
        config = ZapScanConfiguration(scan_type=ZapScanType.standard)
        cmd = build_zap_command("http://127.0.0.1;rm -rf /", config)
        self.assertIn("http://127.0.0.1;rm -rf /", cmd)
        self.assertEqual(cmd[cmd.index("-quickurl") + 1], "http://127.0.0.1;rm -rf /")

    # Requirement 4: Strictly typed profiles, passive cannot active scan
    def test_passive_cannot_active_scan(self):
        from pydantic import ValidationError
        with self.assertRaises(ValueError):
            ZapScanConfiguration(scan_type=ZapScanType.passive, active_scan=True)

    # Requirement 5: FileNotFoundError -> ScannerError
    @patch("subprocess.run")
    def test_zap_missing_raises_error(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaisesRegex(ScannerError, "ZAP executable not found"):
            self.adapter.scan("http://127.0.0.1", "passive")

    # Requirement 6: TimeoutExpired -> ScannerError
    @patch("subprocess.run")
    def test_timeout_raises_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["zap"], timeout=600)
        with self.assertRaisesRegex(ScannerError, "Scan timed out"):
            self.adapter.scan("http://127.0.0.1", "passive")

    # Requirement 7: Non-zero exit without usable output -> ScannerError
    @patch("subprocess.run")
    def test_non_zero_exit_no_output(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Fatal Java Exception"
        mock_run.return_value = mock_result
        
        with self.assertRaisesRegex(ScannerError, "Fatal Java Exception"):
            self.adapter.scan("http://127.0.0.1", "passive")

    # Requirement 8: Malformed/empty JSON safely handled
    def test_malformed_json_safe(self):
        self.assertEqual(parse_zap_json(""), [])
        self.assertEqual(parse_zap_json("{ invalid json"), [])

    # Requirements 9 & 10: Valid JSON -> ScannerResult, Multiple alerts -> Multiple Findings
    def test_zap_json_parsing(self):
        json_data = {
            "alerts": [
                {
                    "alert": "Alert 1",
                    "risk": "High",
                    "instances": [{"uri": "http://127.0.0.1"}]
                },
                {
                    "alert": "Alert 2",
                    "risk": "Low",
                    "instances": [{"uri": "http://127.0.0.2"}]
                }
            ]
        }
        findings = parse_zap_json(json.dumps(json_data))
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].title, "Alert 1")
        self.assertEqual(findings[1].title, "Alert 2")

    # Requirement 11: Severity mappings
    def test_severity_mapping(self):
        self.assertEqual(map_severity("Informational"), "info")
        self.assertEqual(map_severity("Low"), "low")
        self.assertEqual(map_severity("Medium"), "medium")
        self.assertEqual(map_severity("High"), "high")

    # Requirement 12: Confidence mappings
    def test_confidence_mapping(self):
        self.assertEqual(map_confidence("False Positive"), "low")
        self.assertEqual(map_confidence("Low"), "low")
        self.assertEqual(map_confidence("Medium"), "medium")
        self.assertEqual(map_confidence("High"), "high")
        self.assertEqual(map_confidence("Confirmed"), "high")

    # Requirement 13: Fields preserved
    def test_finding_preserves_fields(self):
        json_data = {
            "alerts": [{
                "alert": "Test Alert",
                "risk": "Medium",
                "confidence": "High",
                "description": "Test Desc",
                "solution": "Test Sol",
                "otherinfo": "Test Impact",
                "instances": [{"uri": "http://127.0.0.1/test"}]
            }]
        }
        f = parse_zap_json(json.dumps(json_data))[0]
        self.assertEqual(f.title, "Test Alert")
        self.assertEqual(f.severity, "medium")
        self.assertEqual(f.confidence, "high")
        self.assertEqual(f.description, "Test Desc")
        self.assertEqual(f.remediation, "Test Sol")
        self.assertEqual(f.impact, "Test Impact")
        self.assertEqual(f.category, "Web Vulnerability")
        self.assertEqual(f.location, "http://127.0.0.1/test")

    # Requirement 14: Multiple locations handled
    def test_multiple_locations_handled(self):
        json_data = {
            "alerts": [{
                "alert": "Test Alert",
                "instances": [
                    {"uri": "http://127.0.0.1/1"},
                    {"uri": "http://127.0.0.1/2"}
                ]
            }]
        }
        f = parse_zap_json(json.dumps(json_data))[0]
        self.assertEqual(f.location, "http://127.0.0.1/1, http://127.0.0.1/2")
        self.assertIn("found in 2 locations", f.description)
        self.assertEqual(len(f.evidence), 2)

    # Requirement 15: Evidence redacts secrets
    def test_evidence_redacts_secrets(self):
        content = "Authorization: Bearer secret_token\nCookie: session=12345\nPassword: mysecretpassword\nSafe Data"
        redacted = redact_secrets(content)
        self.assertNotIn("secret_token", redacted)
        self.assertNotIn("12345", redacted)
        self.assertNotIn("mysecretpassword", redacted)
        self.assertIn("[REDACTED]", redacted)
        self.assertIn("Safe Data", redacted)

    # Requirement 16: Worker propagates ScannerError to ScanJobStatus.failed
    def test_worker_catches_zap_scanner_error(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        p = Project(name="Test")
        db.add(p)
        db.flush()
        
        a = Assessment(project_id=p.id, name="Test", target="http://127.0.0.1", scope="Test", authorization_confirmed=True)
        db.add(a)
        db.flush()
        
        job = ScanJob(assessment_id=a.id, scan_profile="standard")
        db.add(job)
        db.commit()
        
        with patch("app.worker.service.get_scanner") as mock_get_scanner:
            mock_scanner = MagicMock()
            mock_scanner.scan.side_effect = ScannerError("Mocked ZAP missing")
            mock_get_scanner.return_value = mock_scanner
            
            processed_job = process_scan_job(db, job.id)
            
            self.assertEqual(processed_job.status, ScanJobStatus.failed)
            self.assertIn("Scanner error: Mocked ZAP missing", processed_job.error_message)

if __name__ == "__main__":
    unittest.main()
