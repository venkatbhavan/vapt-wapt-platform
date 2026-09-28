from enum import Enum
from pydantic import BaseModel, model_validator
from typing import List

class ZapScanType(str, Enum):
    passive = "passive"
    standard = "standard"
    active = "active"

class ZapScanConfiguration(BaseModel):
    scan_type: ZapScanType = ZapScanType.standard
    spider: bool = True
    ajax_spider: bool = False
    active_scan: bool = False

    @model_validator(mode='after')
    def validate_configuration(self):
        # Enforce that passive scans do not active_scan
        if self.scan_type == ZapScanType.passive and self.active_scan:
            raise ValueError("Passive profile cannot perform active scanning")
        return self

def get_zap_config_for_profile(scan_profile: str) -> ZapScanConfiguration:
    sp = scan_profile.lower()
    
    if sp == "passive":
        return ZapScanConfiguration(scan_type=ZapScanType.passive, active_scan=False)
    elif sp == "active":
        return ZapScanConfiguration(scan_type=ZapScanType.active, active_scan=True)
    
    # standard is default
    return ZapScanConfiguration(scan_type=ZapScanType.standard, active_scan=False)

def build_zap_command(target: str, config: ZapScanConfiguration) -> List[str]:
    # Mocking a realistic CLI command construction for ZAP
    cmd = ["zap", "-cmd", "-quickurl", target, "-quickout", "-"]
    
    if config.scan_type == ZapScanType.active or config.active_scan:
        cmd.append("-active")
        
    return cmd
