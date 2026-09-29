import xml.etree.ElementTree as ET
from typing import List, Tuple
from .models import Finding, EvidenceItem, HostObservation, ServiceObservation

def parse_nmap_xml(xml_content: str) -> Tuple[List[Finding], List[HostObservation]]:
    """
    Parses Nmap XML output and normalizes it into Finding objects and HostObservations.
    """
    findings = []
    hosts_out = []

    if not xml_content or not xml_content.strip():
        return findings, hosts_out

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return findings, hosts_out

    for host in root.findall('host'):
        status = host.find('status')
        if status is not None and status.get('state') != 'up':
            continue

        address = ""
        addr_elem = host.find('address')
        if addr_elem is not None:
            address = addr_elem.get('addr', '')

        # Hostnames
        hostname_str = None
        hostnames_elem = host.find('hostnames')
        if hostnames_elem is not None:
            first_hn = hostnames_elem.find('hostname')
            if first_hn is not None:
                hostname_str = first_hn.get('name')

        host_obs = HostObservation(
            ip_address=address or "unknown",
            hostname=hostname_str,
            os=None,  # Not extracting OS for now unless it's easy, let's keep it simple
            services=[]
        )

        ports = host.find('ports')
        if ports is not None:
            for port in ports.findall('port'):
                state_elem = port.find('state')
                if state_elem is None:
                    continue
                state_val = state_elem.get('state', 'unknown')

                protocol = port.get('protocol', 'tcp')
                port_id_str = port.get('portid', '')
                try:
                    port_id = int(port_id_str)
                except ValueError:
                    continue

                reason = state_elem.get('reason', 'unknown')

                service_name = "unknown"
                service_product = ""
                service_version = ""
                service_extrainfo = ""
                service_elem = port.find('service')
                if service_elem is not None:
                    service_name = service_elem.get('name', 'unknown')
                    service_product = service_elem.get('product', '')
                    service_version = service_elem.get('version', '')
                    service_extrainfo = service_elem.get('extrainfo', '')

                # Attack Surface Observation
                svc_obs = ServiceObservation(
                    port=port_id,
                    protocol=protocol,
                    state=state_val,
                    service_name=service_name if service_name != 'unknown' else None,
                    service_product=service_product if service_product else None,
                    service_version=service_version if service_version else None,
                    extra_info=service_extrainfo if service_extrainfo else None
                )
                host_obs.services.append(svc_obs)

                # Original Finding Generation (only for open ports)
                if state_val != 'open':
                    continue

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

        if address: # Only append if we found an IP address
            hosts_out.append(host_obs)

    return findings, hosts_out
