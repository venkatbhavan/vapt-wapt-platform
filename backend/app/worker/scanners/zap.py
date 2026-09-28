import subprocess
import logging
from typing import List, Tuple
from .base import ScannerAdapter
from .models import ScannerResult, Finding, ScannerError, EvidenceItem
from .zap_config import get_zap_config_for_profile, build_zap_command
from .zap_parser import parse_zap_json

logger = logging.getLogger(__name__)

class ZapScannerAdapter(ScannerAdapter):
    def __init__(self, timeout: int = 600):
        self.timeout = timeout

    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        config = get_zap_config_for_profile(scan_profile)
        cmd = build_zap_command(target, config)
        
        json_output, error_msg, returncode = self._execute_zap(cmd)
        
        if error_msg and not json_output.strip():
            # Failed before producing any JSON output
            raise ScannerError(error_msg)
            
        findings = []
        if json_output.strip():
            findings = parse_zap_json(json_output)
            
        if returncode != 0:
            # Partial/Error state with some output or fatal failure after partial JSON
            err_finding = Finding(
                title="ZAP Scan Completed with Errors",
                severity="info",
                description="The ZAP process exited with a non-zero status code, indicating a partial or failed scan.",
                category="Scanner Error",
                evidence=[EvidenceItem(
                    evidence_type="text",
                    title="ZAP Stderr",
                    content=error_msg or "Unknown non-zero exit",
                    source="owasp-zap"
                )]
            )
            findings.append(err_finding)
            
        return ScannerResult(
            scanner="zap",
            target=target,
            scan_profile=scan_profile,
            findings=findings
        )

    def _execute_zap(self, cmd: List[str]) -> Tuple[str, str, int]:
        """
        Executes ZAP safely, returning (json_output, error_message, returncode).
        Catches timeouts and missing executable gracefully.
        """
        try:
            # shell=False ALWAYS for security to prevent command injection
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False
            )
            
            return result.stdout, result.stderr, result.returncode

        except FileNotFoundError:
            logger.error("ZAP executable not found.")
            return "", "ZAP executable not found", 1
        except subprocess.TimeoutExpired:
            logger.error(f"ZAP scan timed out after {self.timeout} seconds.")
            return "", "Scan timed out", 1
        except Exception as e:
            logger.error(f"Unexpected error executing ZAP: {str(e)}")
            return "", f"Unexpected error: {str(e)}", 1
