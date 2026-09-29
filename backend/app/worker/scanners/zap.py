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
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            logger.error(f"ZAP API HTTP error {e.code}: {e.reason}")
            error_body = e.read().decode('utf-8') if e.fp else ""
            raise ScannerError(f"ZAP API HTTP error {e.code}: {e.reason}. Details: {error_body}")
        except urllib.error.URLError as e:
            logger.error(f"ZAP API connection error: {e}")
            raise ScannerError(f"ZAP API connection failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"ZAP API decode error: {e}")
            raise ScannerError(f"Invalid JSON from ZAP API: {e}")

    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        config = get_zap_config_for_profile(scan_profile)
        try:
            zap_target = target
            if "127.0.0.1" in zap_target:
                zap_target = zap_target.replace("127.0.0.1", "host.docker.internal")

            encoded_target = urllib.parse.quote(zap_target, safe='')
            spider_res = self._api_request(f"spider/action/scan/?url={encoded_target}")
            scan_id = spider_res.get("scan")
            if scan_id is None:
                raise ScannerError(f"Failed to start ZAP spider. Response: {spider_res}")

            start_time = time.time()
            while True:
                if time.time() - start_time > self.timeout:
                    raise ScannerError(f"ZAP scan timed out after {self.timeout} seconds.")
                status_res = self._api_request(f"spider/view/status/?scanId={scan_id}")
                if int(status_res.get("status", 0)) >= 100:
                    break
                time.sleep(2)

            while True:
                if time.time() - start_time > self.timeout:
                    raise ScannerError(f"ZAP passive scan timed out waiting for records to empty.")
                records_res = self._api_request("pscan/view/recordsToScan/")
                if int(records_res.get("recordsToScan", 100)) == 0:
                    break
                time.sleep(1)

            if config.active_scan:
                ascan_res = self._api_request(f"ascan/action/scan/?url={encoded_target}")
                ascan_id = ascan_res.get("scan")
                if ascan_id is None:
                    raise ScannerError(f"Failed to start ZAP active scan. Response: {ascan_res}")
                while True:
                    if time.time() - start_time > self.timeout:
                        raise ScannerError(f"ZAP active scan timed out after {self.timeout} seconds.")
                    ascan_status_res = self._api_request(f"ascan/view/status/?scanId={ascan_id}")
                    if int(ascan_status_res.get("status", 0)) >= 100:
                        break
                    time.sleep(2)

                alerts_ids_res = self._api_request(f"ascan/view/alertsIds/?scanId={ascan_id}")
                alert_ids = alerts_ids_res.get("alertsIds", [])

                raw_alerts = []
                for a_id in alert_ids:
                    a_res = self._api_request(f"core/view/alert/?id={a_id}")
                    if "alert" in a_res:
                        raw_alerts.append(a_res["alert"])

                alerts_json = json.dumps({"alerts": raw_alerts})
            else:
                alerts_res = self._api_request(f"core/view/alerts/?baseurl={encoded_target}")
                alerts_json = json.dumps(alerts_res)

            alerts_json = alerts_json.replace("host.docker.internal", "127.0.0.1")

            findings = parse_zap_json(alerts_json)

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
