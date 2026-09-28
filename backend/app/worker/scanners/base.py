from abc import ABC, abstractmethod
from .models import ScannerResult

class ScannerAdapter(ABC):
    """
    Abstract Base Class defining the contract for all scanner adapters.
    """
    @abstractmethod
    def scan(self, target: str, scan_profile: str) -> ScannerResult:
        """
        Execute the scan against the target using the specified profile.
        Must return a structured ScannerResult.
        """
        pass
