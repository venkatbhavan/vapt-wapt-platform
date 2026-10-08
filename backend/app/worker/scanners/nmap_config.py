from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional

class TcpScanType(str, Enum):
    connect = "connect"   # -sT
    syn = "syn"           # -sS
    ack = "ack"           # -sA
    window = "window"     # -sW
    maimon = "maimon"     # -sM
    fin = "fin"           # -sF
    null = "null"         # -sN
    xmas = "xmas"         # -sX
    none = "none"

class PortSelection(str, Enum):
    common = "common"     # Default
    all = "all"           # -p-

class NmapScanConfiguration(BaseModel):
    tcp_scan: TcpScanType = TcpScanType.syn
    tcp_ports: Optional[PortSelection] = PortSelection.common
    udp_scan: bool = False
    udp_ports: Optional[PortSelection] = None
    service_detection: bool = False
    os_detection: bool = False
    default_scripts: bool = False
    host_discovery: bool = False
    traceroute: bool = False
    aggressive: bool = False

    @model_validator(mode='after')
    def validate_configuration(self):
        # Enforce that UDP ports are only set if UDP scan is enabled
        if self.udp_ports and not self.udp_scan:
            raise ValueError("udp_ports cannot be set without udp_scan=True")
        # Host discovery shouldn't combine coherently with port-specific flags
        if self.host_discovery:
            if self.tcp_ports or self.udp_ports or self.service_detection or self.os_detection:
                raise ValueError("host_discovery is incompatible with port scanning options")
        return self

def get_nmap_config_for_profile(scan_profile: str) -> NmapScanConfiguration:
    sp = scan_profile.lower()
    
    if sp == "safe":
        return NmapScanConfiguration(tcp_scan=TcpScanType.connect, tcp_ports=PortSelection.common)
    elif sp == "standard":
        return NmapScanConfiguration(tcp_scan=TcpScanType.syn, service_detection=True, default_scripts=True)
    elif sp == "deep":
        return NmapScanConfiguration(
            tcp_scan=TcpScanType.syn, tcp_ports=PortSelection.all,
            service_detection=True, os_detection=True,
            default_scripts=True, traceroute=True
        )
    elif sp == "udp":
        return NmapScanConfiguration(tcp_scan=TcpScanType.none, tcp_ports=None, udp_scan=True, udp_ports=PortSelection.common)
    elif sp == "stealth" or sp == "syn":
        return NmapScanConfiguration(tcp_scan=TcpScanType.syn)
    elif sp == "fin":
        return NmapScanConfiguration(tcp_scan=TcpScanType.fin)
    elif sp == "null":
        return NmapScanConfiguration(tcp_scan=TcpScanType.null)
    elif sp == "xmas":
        return NmapScanConfiguration(tcp_scan=TcpScanType.xmas)
    elif sp == "ack":
        return NmapScanConfiguration(tcp_scan=TcpScanType.ack)
    elif sp == "window":
        return NmapScanConfiguration(tcp_scan=TcpScanType.window)
    elif sp == "maimon":
        return NmapScanConfiguration(tcp_scan=TcpScanType.maimon)
    elif sp == "aggressive":
        return NmapScanConfiguration(tcp_scan=TcpScanType.syn, aggressive=True)
    elif sp == "full":
        # Internally coherent full scan: TCP SYN + UDP + Aggressive
        return NmapScanConfiguration(
            tcp_scan=TcpScanType.syn, tcp_ports=PortSelection.all,
            udp_scan=True, udp_ports=PortSelection.all,
            aggressive=True
        )
    elif sp == "discovery":
        return NmapScanConfiguration(
            tcp_scan=TcpScanType.none, tcp_ports=None, host_discovery=True
        )
    
    # Fallback
    return NmapScanConfiguration()

def build_nmap_command(target: str, config: NmapScanConfiguration) -> List[str]:
    # Defence in depth: arrays avoid shell injection, but a target such as "--script=..."
    # would still be parsed by nmap as an option, so reject option-like or malformed targets.
    if not target or target.startswith("-") or any(ch.isspace() or ord(ch) < 32 for ch in target):
        raise ValueError("Invalid scan target")
    cmd = ["nmap", "-oX", "-"]

    if config.host_discovery:
        cmd.append("-sn")
        cmd.append(target)
        return cmd

    # TCP Scan Type
    scan_type_map = {
        TcpScanType.connect: "-sT",
        TcpScanType.syn: "-sS",
        TcpScanType.ack: "-sA",
        TcpScanType.window: "-sW",
        TcpScanType.maimon: "-sM",
        TcpScanType.fin: "-sF",
        TcpScanType.null: "-sN",
        TcpScanType.xmas: "-sX"
    }

    if config.tcp_scan != TcpScanType.none:
        flag = scan_type_map.get(config.tcp_scan)
        if flag:
            cmd.append(flag)

    # UDP Scan
    if config.udp_scan:
        cmd.append("-sU")

    # Ports
    port_parts = []
    if config.tcp_scan != TcpScanType.none and config.tcp_ports == PortSelection.all:
        port_parts.append("T:1-65535")
    if config.udp_scan and config.udp_ports == PortSelection.all:
        port_parts.append("U:1-65535")

    if port_parts:
        cmd.extend(["-p", ",".join(port_parts)])

    # Aggressive includes OS (-O), Version (-sV), Script (-sC) and Traceroute (--traceroute)
    if config.aggressive:
        cmd.append("-A")
    else:
        if config.service_detection:
            cmd.append("-sV")
        if config.os_detection:
            cmd.append("-O")
        if config.default_scripts:
            cmd.append("-sC")
        if config.traceroute:
            cmd.append("--traceroute")

    cmd.append(target)
    return cmd
