from .base import ScannerAdapter
from .mock import MockScannerAdapter

# Future placeholders for real scanner adapters
# from .nmap import NmapScannerAdapter
# from .zap import ZAPScannerAdapter

def get_scanner(scan_profile: str) -> ScannerAdapter:
    """
    Factory function to retrieve the appropriate scanner adapter.
    Currently, strictly resolves to MockScannerAdapter to prevent external execution.
    """
    # In the future, this might dispatch based on the profile:
    # if scan_profile == "deep":
    #     return ZAPScannerAdapter()
    # elif scan_profile == "standard":
    #     return NmapScannerAdapter()
    
    return MockScannerAdapter()
