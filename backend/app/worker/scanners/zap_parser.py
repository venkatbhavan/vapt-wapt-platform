import re
import json
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Optional
from .models import Finding, EvidenceItem, WebApplicationObservation, WebEndpointObservation

def map_severity(zap_risk: str) -> str:
    risk = zap_risk.lower().strip()
    if "informational" in risk: return "info"
    if "low" in risk: return "low"
    if "medium" in risk: return "medium"
    if "high" in risk: return "high"
    return "info"

def map_confidence(zap_conf: str) -> str:
    conf = zap_conf.lower().strip()
    if "false positive" in conf: return "low"
    if "low" in conf: return "low"
    if "medium" in conf: return "medium"
    if "high" in conf: return "high"
    if "confirmed" in conf: return "high"
    return "low"

def redact_secrets(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'(?i)(cookie\s*[:=]\s*)[^\r\n]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)(authorization\s*[:=]\s*Bearer\s+)[^\r\n]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)(password\s*[:=]\s*)[^\r\n&]+', r'\1[REDACTED]', text)
    return text

def normalize_url(raw_url: str, method: str = "GET") -> Optional[Tuple[str, str, str, int, str, str]]:
    if not raw_url:
        return None

    try:
        parsed = urlparse(raw_url)
        if not parsed.scheme or not parsed.netloc:
            return None

        scheme = parsed.scheme.lower()
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        if not hostname:
            return None

        if parsed.port:
            port = parsed.port
        else:
            port = 443 if scheme == "https" else 80

        base_url = f"{scheme}://{hostname}"
        if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
            base_url += f":{port}"

        path = parsed.path
        if not path:
            path = "/"
        if not path.startswith("/"):
            path = "/" + path

        norm_method = method.upper().strip() if method else "GET"
        if not norm_method:
            norm_method = "GET"

        return base_url, scheme, hostname, port, path, norm_method

    except Exception:
        return None


def parse_zap_json(json_content: str, raw_urls: List[str] = None) -> Tuple[List[Finding], List[WebApplicationObservation]]:
    findings = []
    web_apps_map: Dict[str, WebApplicationObservation] = {}
    endpoints_set = set() # (base_url, path, method)

    if raw_urls is None:
        raw_urls = []

    def _process_url(url: str, method: str = "GET", discovered_from: str = None):
        norm = normalize_url(url, method)
        if not norm:
            return
        base_url, scheme, hostname, port, path, norm_method = norm

        if base_url not in web_apps_map:
            web_apps_map[base_url] = WebApplicationObservation(
                base_url=base_url,
                scheme=scheme,
                hostname=hostname,
                port=port,
                endpoints=[]
            )

        ep_key = (base_url, path, norm_method)
        if ep_key not in endpoints_set:
            endpoints_set.add(ep_key)
            ep = WebEndpointObservation(
                url=url, # Keep first seen full URL for reference
                path=path,
                method=norm_method,
                discovered_from=discovered_from
            )
            web_apps_map[base_url].endpoints.append(ep)


    # Pre-process raw urls
    for r_url in raw_urls:
        _process_url(r_url, discovered_from="zap_spider")

    if not json_content or not json_content.strip():
        return findings, list(web_apps_map.values())

    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return findings, list(web_apps_map.values())

    raw_alerts = data.get("alerts", [])

    grouped_alerts = {}
    for alert in raw_alerts:
        title = alert.get("name") or alert.get("alert") or "Unknown ZAP Alert"
        url = alert.get("url", "")

        if url:
            _process_url(url, method=alert.get("method", "GET"), discovered_from="zap_alert")

        key = f"{title}::{url}"

        if key not in grouped_alerts:
            grouped_alerts[key] = {k: v for k, v in alert.items() if k != "instances"}
            grouped_alerts[key]["instances"] = []

        if "instances" in alert and alert["instances"]:
            grouped_alerts[key]["instances"].extend(alert["instances"])
        elif any(k in alert for k in ("url", "evidence", "attack", "param")):
            inst = {
                "uri": alert.get("url", ""),
                "param": alert.get("param", ""),
                "attack": alert.get("attack", ""),
                "evidence": alert.get("evidence", ""),
                "method": alert.get("method", "GET")
            }
            grouped_alerts[key]["instances"].append(inst)

    for alert in grouped_alerts.values():
        title = alert.get("name") or alert.get("alert") or "Unknown ZAP Alert"
        severity = map_severity(alert.get("risk", "Informational"))
        confidence = map_confidence(alert.get("confidence", "Low"))
        description = alert.get("description", "")
        remediation = alert.get("solution", "")
        impact = alert.get("otherinfo", "")

        cwe = alert.get("cweid")
        if cwe and cwe != "-1":
            description += f"\n\nCWE: {cwe}"
        cve = alert.get("wascid") or alert.get("cveid")
        if cve and cve != "-1":
            description += f"\n\nWASC ID: {cve}"
        reference = alert.get("reference")
        if reference:
            description += f"\n\nReferences:\n{reference}"

        instances = alert.get("instances", [])

        # Also map instances' urls for attack surface!
        for inst in instances:
            i_uri = inst.get("uri")
            i_meth = inst.get("method", "GET")
            if i_uri:
                _process_url(i_uri, method=i_meth, discovered_from="zap_alert_instance")

        unique_uris = list(dict.fromkeys(inst.get("uri", "") for inst in instances if inst.get("uri")))
        location = ", ".join(unique_uris)[:255] if unique_uris else ""

        if len(instances) > 1:
            description += f"\n\nNote: This issue was found with {len(instances)} parameter/attack variations at this location. See evidence for details."

        evidence_list = []
        for idx, inst in enumerate(instances):
            uri = inst.get("uri", "")
            param = inst.get("param", "")
            attack = inst.get("attack", "")
            evidence = inst.get("evidence", "")

            content_parts = []
            if uri: content_parts.append(f"URI: {uri}")
            if param: content_parts.append(f"Parameter: {param}")
            if attack: content_parts.append(f"Attack: {attack}")
            if evidence: content_parts.append(f"Evidence: {evidence}")

            content = redact_secrets("\n".join(content_parts))

            evidence_list.append(EvidenceItem(
                evidence_type="zap_alert_instance",
                title=f"ZAP Alert Instance {idx+1}",
                content=content,
                source="owasp-zap"
            ))

        findings.append(Finding(
            title=title,
            severity=severity,
            description=description,
            confidence=confidence,
            category="Web Vulnerability",
            location=location,
            impact=impact,
            remediation=remediation,
            evidence=evidence_list
        ))

    return findings, list(web_apps_map.values())
