import subprocess
from typing import List, Tuple
from .base import ScannerAdapter
from .models import ScannerResult, Finding, ScannerError, EvidenceItem
from .nmap_config import get_nmap_config_for_profile, build_nmap_command
from .nmap_parser import parse_nmap_xml
import logging

logger = logging.getLogger(__name__)

class NmapScannerAdapter(ScannerAdapter):
    def __init__(self, timeout: int = 300):
        self.timeout = timeout

    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        config = get_nmap_config_for_profile(scan_profile)
        cmd = build_nmap_command(target, config)
        
        xml_output, error_msg, returncode = self._execute_nmap(cmd)
        
        if error_msg and not xml_output.strip():
            # Failed before producing any XML output
            raise ScannerError(error_msg)
            
        findings = []
        if xml_output.strip():
            findings = parse_nmap_xml(xml_output)
            
        if returncode != 0:
            # Partial/Error state with some XML
            err_finding = Finding(
                title="Scan Completed with Errors",
                severity="info",
                description="The Nmap process exited with a non-zero status code, indicating a partial or failed scan.",
                category="Scanner Error",
                evidence=[EvidenceItem(
                    evidence_type="text",
                    title="Nmap Stderr",
                    content=error_msg or "Unknown non-zero exit",
                    source="nmap"
                )]
            )
            findings.append(err_finding)
            
        return ScannerResult(
            scanner="nmap",
            target=target,
            scan_profile=scan_profile,
            findings=findings
        )

    def _execute_nmap(self, cmd: List[str]) -> Tuple[str, str, int]:
        """
        Executes Nmap safely, returning (xml_output, error_message, returncode).
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
            logger.error("Nmap executable not found.")
            return "", "Nmap executable not found", 1
        except subprocess.TimeoutExpired:
            logger.error(f"Nmap scan timed out after {self.timeout} seconds.")
            return "", "Scan timed out", 1
        except Exception as e:
            logger.error(f"Unexpected error executing Nmap: {str(e)}")
            return "", f"Unexpected error: {str(e)}", 1
