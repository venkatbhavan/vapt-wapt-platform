import unittest
from unittest.mock import patch
from app.worker.scanners.models import ScannerResult, WebApplicationObservation, WebEndpointObservation
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.models.assessment import ScanJobStatus
from test_zap_attack_surface import TestZapAttackSurfaceIngestion

class TestZapAttackSurfaceExtra(TestZapAttackSurfaceIngestion):

    # 1. IP-based ZAP URL creates Asset with valid IP.
    def test_extra_01_ip_based_creates_ip(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://192.168.1.100:80", scheme="http", hostname="192.168.1.100", port=80)]
        )
        self._run_zap_job(res)
        asset = self.db.query(Asset).first()
        self.assertEqual(asset.ip_address, "192.168.1.100")
        self.assertIsNone(asset.hostname)

    # 2. Hostname-based ZAP URL does NOT place hostname into Asset.ip_address.
    @patch('socket.gethostbyname')
    def test_extra_02_hostname_does_not_pollute_ip(self, mock_dns):
        mock_dns.return_value = "10.0.0.5"
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://test.local:80", scheme="http", hostname="test.local", port=80)]
        )
        self._run_zap_job(res)
        asset = self.db.query(Asset).first()
        self.assertEqual(asset.ip_address, "10.0.0.5")
        self.assertEqual(asset.hostname, "test.local")
        
    @patch('socket.gethostbyname')
    def test_extra_02b_hostname_schema_limitation(self, mock_dns):
        mock_dns.side_effect = Exception("No DNS")
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://test.local:80", scheme="http", hostname="test.local", port=80)]
        )
        self._run_zap_job(res)
        # Should be skipped, no asset created
        self.assertEqual(self.db.query(Asset).count(), 0)

    # 3. Existing Asset with matching hostname is associated only when identity is unambiguous.
    @patch('socket.gethostbyname')
    def test_extra_03_existing_hostname_matches(self, mock_dns):
        # We don't even call DNS if exact hostname matches
        mock_dns.side_effect = Exception("Should not be called")
        
        # Pre-seed Nmap asset
        asset = Asset(assessment_id=self.assessment.id, ip_address="10.0.0.9", hostname="server-a")
        self.db.add(asset)
        self.db.commit()
        
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://server-a:80", scheme="http", hostname="server-a", port=80)]
        )
        self._run_zap_job(res)
        
        # Must link to the existing one
        self.assertEqual(self.db.query(Asset).count(), 1)
        self.assertEqual(self.db.query(Asset).first().ip_address, "10.0.0.9")

    # 5. IP and hostname representations cannot accidentally cross-associate.
    @patch('socket.gethostbyname')
    def test_extra_05_no_accidental_cross_association(self, mock_dns):
        mock_dns.return_value = "10.0.0.100"
        
        # Pre-seed Asset with ip 10.0.0.5 and hostname server-a
        asset = Asset(assessment_id=self.assessment.id, ip_address="10.0.0.5", hostname="server-a")
        self.db.add(asset)
        self.db.commit()
        
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            # This hostname does not match "server-a", so it attempts DNS resolve.
            # DNS gives 10.0.0.100, which doesn't match 10.0.0.5
            web_applications=[WebApplicationObservation(base_url="http://server-b:80", scheme="http", hostname="server-b", port=80)]
        )
        self._run_zap_job(res)
        
        self.assertEqual(self.db.query(Asset).count(), 2)

    # 8. Explicit default port and implicit default port do not create duplicate WebApplications.
    def test_extra_08_implicit_explicit_ports(self):
        res1 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1", scheme="http", hostname="127.0.0.1", port=80)]
        )
        res2 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="full",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res1)
        self._run_zap_job(res2)
        
        self.assertEqual(self.db.query(WebApplication).count(), 1)
        
if __name__ == "__main__":
    unittest.main()
