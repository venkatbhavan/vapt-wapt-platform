import unittest
import json
import urllib.error
from unittest.mock import patch, MagicMock
from app.worker.scanners.zap import ZapScannerAdapter
from app.worker.scanners.zap_config import (
    ZapScanConfiguration, ZapScanType, get_zap_config_for_profile
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

    @patch("urllib.request.urlopen")
    def test_target_argument_safety_http(self, mock_urlopen):
        def create_mock_response(body):
            mock_resp = MagicMock()
            mock_resp.read.return_value = body
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        def side_effect(req, timeout=10):
            url = req.full_url
            if "spider/action/scan" in url: return create_mock_response(b'{"scan": "1"}')
            elif "spider/view/status" in url: return create_mock_response(b'{"status": "100"}')
            elif "pscan/view/recordsToScan" in url: return create_mock_response(b'{"recordsToScan": "0"}')
            elif "core/view/alerts" in url: return create_mock_response(b'{"alerts": []}')
            return create_mock_response(b'{}')

        mock_urlopen.side_effect = side_effect

        target = "http://127.0.0.1;echo-test"
        self.adapter.scan(target, "passive")

        calls = mock_urlopen.call_args_list
        req_obj = calls[0][0][0]
        self.assertIn("host.docker.internal", req_obj.full_url)
        self.assertEqual(req_obj.get_header("X-zap-api-key"), "VAPT_LOCAL_TEST_KEY_2026")

    @patch("urllib.request.urlopen")
    def test_active_scan_workflow(self, mock_urlopen):
        def create_mock_response(body):
            mock_resp = MagicMock()
            mock_resp.read.return_value = body
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        def side_effect(req, timeout=10):
            url = req.full_url
            if "spider/action/scan" in url: return create_mock_response(b'{"scan": "1"}')
            elif "spider/view/status" in url: return create_mock_response(b'{"status": "100"}')
            elif "pscan/view/recordsToScan" in url: return create_mock_response(b'{"recordsToScan": "0"}')
            elif "ascan/action/scan" in url: return create_mock_response(b'{"scan": "2"}')
            elif "ascan/view/status" in url: return create_mock_response(b'{"status": "100"}')
            elif "ascan/view/alertsIds" in url: return create_mock_response(b'{"alertsIds": ["1", "2"]}')
            elif "core/view/alert/?id=1" in url: return create_mock_response(b'{"alert": {"name": "Test Alert 1", "url": "http://127.0.0.1", "risk": "High"}}')
            elif "core/view/alert/?id=2" in url: return create_mock_response(b'{"alert": {"name": "Test Alert 2", "url": "http://127.0.0.1", "risk": "Low"}}')
            elif "core/view/alerts" in url: return create_mock_response(b'{"alerts": []}')
            return create_mock_response(b'{}')

        mock_urlopen.side_effect = side_effect

        target = "http://127.0.0.1"
        res = self.adapter.scan(target, "active")

        urls_called = [call[0][0].full_url for call in mock_urlopen.call_args_list]
        self.assertTrue(any("ascan/action/scan" in u for u in urls_called))
        self.assertTrue(any("ascan/view/alertsIds" in u for u in urls_called))
        self.assertTrue(any("core/view/alert/?id=1" in u for u in urls_called))

        self.assertEqual(len(res.findings), 2)
        self.assertEqual(res.findings[0].title, "Test Alert 1")
        self.assertEqual(res.findings[1].title, "Test Alert 2")

    def test_passive_cannot_active_scan(self):
        from pydantic import ValidationError
        with self.assertRaises(ValueError):
            ZapScanConfiguration(scan_type=ZapScanType.passive, active_scan=True)

    @patch("urllib.request.urlopen")
    def test_zap_connection_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with self.assertRaisesRegex(ScannerError, "ZAP API connection failed"):
            self.adapter.scan("http://127.0.0.1", "passive")

    @patch("app.worker.scanners.zap.ZapScannerAdapter._api_request")
    def test_timeout_raises_error(self, mock_api_request):
        def side_effect(endpoint):
            if "spider/action/scan" in endpoint:
                return {"scan": "1"}
            elif "spider/view/status" in endpoint:
                return {"status": "50"}
        mock_api_request.side_effect = side_effect

        adapter = ZapScannerAdapter(timeout=1)
        with self.assertRaisesRegex(ScannerError, "ZAP scan timed out"):
            adapter.scan("http://127.0.0.1", "passive")

    def test_malformed_json_safe(self):
        self.assertEqual(parse_zap_json("")[0], [])
        self.assertEqual(parse_zap_json("{ invalid json")[0], [])

    def test_zap_json_parsing(self):
        json_data = {
            "alerts": [
                {
                    "alert": "Alert 1",
                    "risk": "High",
                    "url": "http://127.0.0.1",
                    "instances": [{"uri": "http://127.0.0.1"}]
                },
                {
                    "alert": "Alert 2",
                    "risk": "Low",
                    "url": "http://127.0.0.2",
                    "instances": [{"uri": "http://127.0.0.2"}]
                }
            ]
        }
        findings, _ = parse_zap_json(json.dumps(json_data))
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].title, "Alert 1")
        self.assertEqual(findings[1].title, "Alert 2")

    def test_severity_mapping(self):
        self.assertEqual(map_severity("Informational"), "info")
        self.assertEqual(map_severity("Low"), "low")
        self.assertEqual(map_severity("Medium"), "medium")
        self.assertEqual(map_severity("High"), "high")

    def test_confidence_mapping(self):
        self.assertEqual(map_confidence("False Positive"), "low")
        self.assertEqual(map_confidence("Low"), "low")
        self.assertEqual(map_confidence("Medium"), "medium")
        self.assertEqual(map_confidence("High"), "high")
        self.assertEqual(map_confidence("Confirmed"), "high")

    def test_finding_preserves_fields(self):
        json_data = {
            "alerts": [{
                "alert": "Test Alert",
                "risk": "Medium",
                "confidence": "High",
                "description": "Test Desc",
                "solution": "Test Sol",
                "otherinfo": "Test Impact",
                "url": "http://127.0.0.1/test",
                "instances": [{"uri": "http://127.0.0.1/test"}]
            }]
        }
        f = parse_zap_json(json.dumps(json_data))[0][0]
        self.assertEqual(f.title, "Test Alert")
        self.assertEqual(f.severity, "medium")
        self.assertEqual(f.confidence, "high")
        self.assertEqual(f.description, "Test Desc")
        self.assertEqual(f.remediation, "Test Sol")
        self.assertEqual(f.impact, "Test Impact")
        self.assertEqual(f.category, "Web Vulnerability")
        self.assertEqual(f.location, "http://127.0.0.1/test")

    def test_multiple_locations_handled(self):
        json_data = {
            "alerts": [{
                "alert": "Test Alert",
                "url": "http://127.0.0.1",
                "instances": [
                    {"uri": "http://127.0.0.1/1"},
                    {"uri": "http://127.0.0.1/2"}
                ]
            }]
        }
        f = parse_zap_json(json.dumps(json_data))[0][0]
        self.assertEqual(f.location, "http://127.0.0.1/1, http://127.0.0.1/2")
        self.assertIn("found with 2 parameter/attack variations", f.description)
        self.assertEqual(len(f.evidence), 2)

    def test_evidence_redacts_secrets(self):
        content = "Authorization: Bearer secret_token\nCookie: session=12345\nPassword: mysecretpassword\nSafe Data"
        redacted = redact_secrets(content)
        self.assertNotIn("secret_token", redacted)
        self.assertNotIn("12345", redacted)
        self.assertNotIn("mysecretpassword", redacted)
        self.assertIn("[REDACTED]", redacted)
        self.assertIn("Safe Data", redacted)

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
