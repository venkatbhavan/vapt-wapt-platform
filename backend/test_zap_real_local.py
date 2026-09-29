import os
import unittest
from app.worker.scanners.zap import ZapScannerAdapter
from app.worker.scanners.models import ScannerResult

class TestZapRealLocal(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("VAPT_RUN_REAL_ZAP_TESTS") == "1", "Skipped unless explicitly enabled via environment variable VAPT_RUN_REAL_ZAP_TESTS=1")
    def test_real_zap_scan(self):
        target = "http://127.0.0.1:3000"
        adapter = ZapScannerAdapter(api_url="http://127.0.0.1:8080", api_key="VAPT_LOCAL_TEST_KEY_2026", timeout=600)
        
        result = adapter.scan(target, "active")
        
        self.assertIsInstance(result, ScannerResult)
        self.assertEqual(result.scanner, "zap")
        self.assertEqual(result.target, target)
        
        print(f"\nReal ZAP Active scan completed successfully. Findings count: {len(result.findings)}")
        for finding in result.findings:
            print(f"- {finding.title} [{finding.severity}]")
            
        # Verify that the result contains real ZAP-derived data (empty or not)
        self.assertIsInstance(result.findings, list)

if __name__ == "__main__":
    unittest.main()
