import unittest
from unittest.mock import patch, MagicMock
import subprocess
from app.worker.scanners.nmap import NmapScannerAdapter
from app.worker.scanners.nmap_config import (
    NmapScanConfiguration, build_nmap_command, TcpScanType, PortSelection, get_nmap_config_for_profile
)
from app.worker.scanners.models import ScannerError
from app.worker.scanners.nmap_parser import parse_nmap_xml
from app.worker.scanners.registry import get_scanner
from app.worker.scanners.mock import MockScannerAdapter
from pydantic import ValidationError

from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus
from app.worker.service import process_scan_job
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestNmapScanner(unittest.TestCase):
    def setUp(self):
        self.adapter = NmapScannerAdapter()

    # Worker Error Integration Test
    def test_worker_catches_scanner_error(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        p = Project(name="Test")
        db.add(p)
        db.flush()
        
        a = Assessment(project_id=p.id, name="Test", target="127.0.0.1", scope="Test", authorization_confirmed=True)
        db.add(a)
        db.flush()
        
        job = ScanJob(assessment_id=a.id, scan_profile="standard")
        db.add(job)
        db.commit()
        
        with patch("app.worker.service.get_scanner") as mock_get_scanner:
            mock_scanner = MagicMock()
            mock_scanner.scan.side_effect = ScannerError("Mocked Nmap missing")
            mock_get_scanner.return_value = mock_scanner
            
            processed_job = process_scan_job(db, job.id)
            
            self.assertEqual(processed_job.status, ScanJobStatus.failed)
            self.assertIn("Scanner error: Mocked Nmap missing", processed_job.error_message)

    # All 14 profiles exactly matching
    def test_profiles_explicitly(self):
        # 1. safe
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("safe"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sT", "127.0.0.1"])
        
        # 2. standard
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("standard"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sS", "-sV", "-sC", "127.0.0.1"])
        
        # 3. deep
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("deep"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sS", "-p", "T:1-65535", "-sV", "-O", "-sC", "--traceroute", "127.0.0.1"])
        
        # 4. udp
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("udp"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sU", "127.0.0.1"])
        
        # 5. syn
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("syn"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sS", "127.0.0.1"])
        
        # 6. fin
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("fin"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sF", "127.0.0.1"])
        
        # 7. null
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("null"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sN", "127.0.0.1"])
        
        # 8. xmas
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("xmas"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sX", "127.0.0.1"])
        
        # 9. ack
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("ack"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sA", "127.0.0.1"])
        
        # 10. window
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("window"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sW", "127.0.0.1"])
        
        # 11. maimon
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("maimon"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sM", "127.0.0.1"])
        
        # 12. aggressive
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("aggressive"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sS", "-A", "127.0.0.1"])
        
        # 13. discovery
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("discovery"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sn", "127.0.0.1"])
        
        # 14. full
        cmd = build_nmap_command("127.0.0.1", get_nmap_config_for_profile("full"))
        self.assertEqual(cmd, ["nmap", "-oX", "-", "-sS", "-sU", "-p", "T:1-65535,U:1-65535", "-A", "127.0.0.1"])

    # Target Argument Safety
    @patch("subprocess.run")
    def test_target_argument_safety(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        target = "127.0.0.1;echo-test"
        self.adapter.scan(target, "safe")
        
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        
        self.assertEqual(kwargs.get("shell"), False)
        self.assertEqual(cmd[-1], target) # Target remains single string argument

    # XML open ports
    def test_xml_one_open_port(self):
        xml_data = """<?xml version="1.0"?><nmaprun><host><status state="up"/><address addr="192.168.1.1"/><ports><port protocol="tcp" portid="80"><state state="open" reason="syn-ack"/></port></ports></host></nmaprun>"""
        findings, hosts = parse_nmap_xml(xml_data)
        self.assertEqual(len(findings), 1)
        self.assertEqual(len(hosts), 1)

    # Missing Nmap raises ScannerError
    @patch("subprocess.run")
    def test_nmap_missing_raises_error(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaisesRegex(ScannerError, "Nmap executable not found"):
            self.adapter.scan("127.0.0.1", "safe")

    # Subprocess timeout raises ScannerError
    @patch("subprocess.run")
    def test_subprocess_timeout_raises_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["nmap"], timeout=300)
        with self.assertRaisesRegex(ScannerError, "Scan timed out"):
            self.adapter.scan("127.0.0.1", "safe")

    # Non-zero exit code with partial XML
    @patch("subprocess.run")
    def test_non_zero_exit_partial_xml(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = """<?xml version="1.0"?><nmaprun><host><status state="up"/><address addr="192.168.1.1"/><ports><port protocol="tcp" portid="80"><state state="open"/></port></ports></host></nmaprun>"""
        mock_result.stderr = "Some nmap warning"
        mock_run.return_value = mock_result
        
        result = self.adapter.scan("127.0.0.1", "safe")
        
        self.assertEqual(len(result.findings), 2)
        titles = [f.title for f in result.findings]
        self.assertIn("Open TCP Service: 80", titles)
        self.assertIn("Scan Completed with Errors", titles)

    # Non-zero exit code without XML
    @patch("subprocess.run")
    def test_non_zero_exit_no_xml(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Fatal error: Nmap cannot run"
        mock_run.return_value = mock_result
        
        with self.assertRaisesRegex(ScannerError, "Fatal error: Nmap cannot run"):
            self.adapter.scan("127.0.0.1", "safe")


    # No arbitrary flags
    def test_no_arbitrary_flags(self):
        with self.assertRaises(ValidationError):
            NmapScanConfiguration(tcp_scan="inject --script=malicious")

if __name__ == "__main__":
    unittest.main()
