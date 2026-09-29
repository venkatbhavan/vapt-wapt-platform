import re
import json
from typing import List
from .models import Finding, EvidenceItem

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

def parse_zap_json(json_content: str) -> List[Finding]:
    findings = []
    if not json_content or not json_content.strip():
        return findings

    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return findings

    raw_alerts = data.get("alerts", [])

    grouped_alerts = {}
    for alert in raw_alerts:
        title = alert.get("name") or alert.get("alert") or "Unknown ZAP Alert"
        url = alert.get("url", "")
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
                "evidence": alert.get("evidence", "")
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

    return findings
