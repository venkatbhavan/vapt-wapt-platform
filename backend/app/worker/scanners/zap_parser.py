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
    # Redact common secrets found in HTTP evidence
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

    alerts = data.get("alerts", [])
    for alert in alerts:
        title = alert.get("alert", "Unknown ZAP Alert")
        severity = map_severity(alert.get("risk", "Informational"))
        confidence = map_confidence(alert.get("confidence", "Low"))
        description = alert.get("description", "")
        remediation = alert.get("solution", "")
        impact = alert.get("otherinfo", "")
        
        instances = alert.get("instances", [])
        
        # Deliberately capture all unique URIs rather than silently discarding them
        unique_uris = list(dict.fromkeys(inst.get("uri", "") for inst in instances if inst.get("uri")))
        location = ", ".join(unique_uris)[:255] if unique_uris else ""
        
        if len(unique_uris) > 1:
            description += f"\n\nNote: This issue was found in {len(unique_uris)} locations. See evidence for details."
            
        evidence_list = []
        for idx, inst in enumerate(instances):
            uri = inst.get("uri", "")
            param = inst.get("param", "")
            evidence = inst.get("evidence", "")
            
            content = f"URI: {uri}"
            if param: content += f"\nParameter: {param}"
            if evidence: content += f"\nEvidence: {evidence}"
            
            # Ensure no credentials/secrets are leaked into evidence
            content = redact_secrets(content)
            
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
