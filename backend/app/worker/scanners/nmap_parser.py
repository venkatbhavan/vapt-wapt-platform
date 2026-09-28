import xml.etree.ElementTree as ET
from typing import List
from .models import Finding, EvidenceItem

def parse_nmap_xml(xml_content: str) -> List[Finding]:
    """
    Parses Nmap XML output and normalizes it into a list of Finding objects.
    Extracts host, ports, services, and handles missing data.
    """
    findings = []
    
    if not xml_content or not xml_content.strip():
        return findings

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        # Malformed XML handled gracefully
        return findings

    for host in root.findall('host'):
        status = host.find('status')
        if status is not None and status.get('state') != 'up':
            continue

        address = ""
        addr_elem = host.find('address')
        if addr_elem is not None:
            address = addr_elem.get('addr', '')

        ports = host.find('ports')
        if ports is not None:
            for port in ports.findall('port'):
                state_elem = port.find('state')
                if state_elem is None or state_elem.get('state') != 'open':
                    continue

                protocol = port.get('protocol', 'tcp')
                port_id = port.get('portid', '')
                reason = state_elem.get('reason', 'unknown')

                service_name = "unknown"
                service_product = ""
                service_version = ""
                service_elem = port.find('service')
                if service_elem is not None:
                    service_name = service_elem.get('name', 'unknown')
                    service_product = service_elem.get('product', '')
                    service_version = service_elem.get('version', '')

                # Normalize into Finding
                title = f"Open {protocol.upper()} Service: {port_id}"
                
                desc_parts = [f"Nmap identified an open {protocol.upper()} service on port {port_id}."]
                if service_product:
                    desc_parts.append(f"Detected service: {service_product} {service_version}".strip())
                desc = " ".join(desc_parts)

                evidence_content = f"Port: {port_id}/{protocol}\nState: open\nReason: {reason}"
                if service_name != 'unknown':
                    evidence_content += f"\nService: {service_name}"
                if service_product:
                    evidence_content += f"\nProduct: {service_product}"
                if service_version:
                    evidence_content += f"\nVersion: {service_version}"

                evidence = EvidenceItem(
                    evidence_type="nmap_port_scan",
                    title=f"Nmap Output for Port {port_id}",
                    content=evidence_content,
                    source="nmap"
                )

                finding = Finding(
                    title=title,
                    severity="info",
                    description=desc,
                    confidence="high",
                    category="Network Exposure",
                    location=f"{address}:{port_id}/{protocol}",
                    impact="Unnecessary exposed services increase the attack surface and can potentially be exploited if vulnerable.",
                    remediation="Disable or restrict access to unnecessary services using firewalls or security groups.",
                    evidence=[evidence]
                )
                
                findings.append(finding)

    return findings
