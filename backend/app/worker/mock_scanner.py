import json

class MockScanner:
    @staticmethod
    def run_scan(target: str, scan_profile: str) -> str:
        """
        MOCK scanner execution. 
        NEVER makes network requests, executes shell commands, or resolves DNS.
        """
        mock_result = {
            "scanner": "mock",
            "target": target,
            "scan_profile": scan_profile,
            "findings": [
                {
                    "title": "Mock Security Finding",
                    "severity": "low",
                    "description": "This is a simulated finding used only for development."
                }
            ]
        }
        return json.dumps(mock_result)
