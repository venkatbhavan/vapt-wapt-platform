from .base import ScannerAdapter
from .models import ScannerResult, Finding

class MockScannerAdapter(ScannerAdapter):
    """
    A deterministic mock scanner used for development and testing.
    Makes zero network requests, executes zero subprocesses, and does not resolve DNS.
    """
    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        return ScannerResult(
            scanner="mock",
            target=target,
            scan_profile=scan_profile,
            findings=[
                Finding(
                    title="Mock Security Finding",
                    severity="low",
                    description="This is a simulated finding used only for development."
                )
            ]
        )
