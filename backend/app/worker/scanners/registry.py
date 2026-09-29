from typing import List, Type
from .base import ScannerAdapter
from .mock import MockScannerAdapter
from .nmap import NmapScannerAdapter
from .zap import ZapScannerAdapter

# Maps a conceptual scan profile to the required scanner(s).
# Using a list allows future evolution where an assessment profile
# might trigger multiple scanner types (e.g. both Nmap and ZAP).
PROFILE_SCANNERS = {
    "safe": [NmapScannerAdapter],
    "standard": [NmapScannerAdapter],
    "ports_only": [NmapScannerAdapter],
    "full": [NmapScannerAdapter],
    "passive": [ZapScannerAdapter],
    "active": [ZapScannerAdapter],
    "deep": [ZapScannerAdapter],
}

def get_scanners(scan_profile: str) -> List[ScannerAdapter]:
    """
    Returns all appropriate scanner adapters for a given profile.
    Allows for multiple scanners per profile in the future.
    """
    scanner_classes = PROFILE_SCANNERS.get(scan_profile)
    if not scanner_classes:
        raise ValueError(f"No appropriate scanner adapter found for profile: {scan_profile}")
    return [cls() for cls in scanner_classes]

def get_scanner(scan_profile: str) -> ScannerAdapter:
    """
    Factory function to retrieve the primary scanner adapter.
    Legacy fallback preserving single-scanner execution behavior.
    """
    return get_scanners(scan_profile)[0]
