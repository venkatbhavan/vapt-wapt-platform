import json
import logging
import urllib.request
import urllib.error
import urllib.parse
import time
from typing import List, Tuple, Dict, Any
from .base import ScannerAdapter
from .models import ScannerResult, Finding, ScannerError, EvidenceItem
from .zap_config import get_zap_config_for_profile
from .zap_parser import parse_zap_json

logger = logging.getLogger(__name__)

class ZapScannerAdapter(ScannerAdapter):
    def __init__(self, api_url: str = "http://127.0.0.1:8080", api_key: str = "VAPT_LOCAL_TEST_KEY_2026", timeout: int = 600):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _api_request(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.api_url}/JSON/{endpoint}"
        req = urllib.request.Request(url)
        req.add_header("X-ZAP-API-Key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            logger.error(f"ZAP API connection error: {e}")
            raise ScannerError(f"ZAP API connection failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"ZAP API decode error: {e}")
            raise ScannerError(f"Invalid JSON from ZAP API: {e}")

    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        # We only support passive scan initially as requested
        config = get_zap_config_for_profile(scan_profile)
        
        try:
            # 1. Start Spider to seed the passive scanner
            encoded_target = urllib.parse.quote(target, safe='')
            spider_res = self._api_request(f"spider/action/scan/?url={encoded_target}")
            scan_id = spider_res.get("scan")
            
            if scan_id is None:
                raise ScannerError(f"Failed to start ZAP spider. Response: {spider_res}")

            # 2. Wait for spider to complete
            start_time = time.time()
            while True:
                if time.time() - start_time > self.timeout:
                    raise ScannerError(f"ZAP scan timed out after {self.timeout} seconds.")
                
                status_res = self._api_request(f"spider/view/status/?scanId={scan_id}")
                if int(status_res.get("status", 0)) >= 100:
                    break
                time.sleep(2)
                
            # 3. Wait for passive scanner to finish processing records
            while True:
                if time.time() - start_time > self.timeout:
                    raise ScannerError(f"ZAP passive scan timed out waiting for records to empty.")
                    
                records_res = self._api_request("pscan/view/recordsToScan/")
                if int(records_res.get("recordsToScan", 100)) == 0:
                    break
                time.sleep(1)

            # 4. Fetch Alerts
            alerts_res = self._api_request("core/view/alerts/")
            
            # Use the existing parser which was updated to handle flat list of alerts
            findings = parse_zap_json(json.dumps(alerts_res))

            return ScannerResult(
                scanner="zap",
                target=target,
                scan_profile=scan_profile,
                findings=findings
            )
            
        except ScannerError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ZAP adapter: {e}")
            raise ScannerError(f"Unexpected error: {str(e)}")
