from typing import Any, Dict
from app.worker.scanners.models import Finding as ScannerFinding

def normalize_finding(scanner_name: str, raw_finding: ScannerFinding) -> Dict[str, Any]:
    """
    Deterministically normalizes a raw scanner finding into Intelligence fields.
    """
    title_lower = raw_finding.title.lower()

    if "missing security header" in title_lower or "missing_security_headers" in title_lower:
        norm_type = "missing_security_headers"
    elif "open port" in title_lower:
        norm_type = "exposed_service"
    elif "sql injection" in title_lower:
        norm_type = "sql_injection"
    elif "xss" in title_lower:
        norm_type = "cross_site_scripting"
    elif "ssh weak" in title_lower:
        norm_type = "weak_ssh_configuration"
    else:
        norm_type = "unknown"

    result = {
        "normalized_type": norm_type,
        "normalized_category": "unknown",
        "root_cause": None,
        "exploitability_context": None,
        "impact": raw_finding.impact, # preserve by default
        "remediation": raw_finding.remediation, # preserve by default
        "evidence_quality": "low",
        "confidence": raw_finding.confidence
    }

    if norm_type == "missing_security_headers":
        result["normalized_category"] = "security_misconfiguration"
        result["root_cause"] = "missing_security_control"
        result["impact"] = "information_disclosure"
        result["remediation"] = "Configure the web server to emit appropriate HTTP security headers such as Strict-Transport-Security and X-Content-Type-Options."
        if scanner_name == "zap":
            result["confidence"] = "high"
            result["evidence_quality"] = "medium"

    elif norm_type == "exposed_service":
        result["normalized_category"] = "network_exposure"
        result["root_cause"] = "insecure_configuration"
        result["impact"] = "network_exposure"
        result["remediation"] = "Disable the service if not required, or restrict network access to trusted IPs using a firewall."
        if scanner_name == "nmap":
            result["confidence"] = "high"
            result["evidence_quality"] = "high"

    elif norm_type == "sql_injection":
        result["normalized_category"] = "injection"
        result["root_cause"] = "improper_input_validation"
        result["impact"] = "confidentiality_integrity_availability_compromise"
        result["remediation"] = "Use parameterized queries or prepared statements for all database access. Avoid string concatenation."
        if scanner_name == "zap":
            result["confidence"] = "medium"
            result["evidence_quality"] = "medium"

    elif norm_type == "cross_site_scripting":
        result["normalized_category"] = "injection"
        result["root_cause"] = "improper_input_validation"
        result["impact"] = "client_side_compromise"
        result["remediation"] = "Implement context-aware output encoding and validate/sanitize all user input."
        if scanner_name == "zap":
            # Only high if proof exists in evidence (e.g., actual payload reflection)
            # For strictness, if ZAP indicates XSS, we might set it if evidence exists.
            has_proof = any(e.content and ("<script>" in e.content or "alert" in e.content or "proof" in (e.title or "").lower()) for e in raw_finding.evidence)
            if has_proof:
                result["confidence"] = "high"
                result["evidence_quality"] = "high"
            else:
                result["confidence"] = raw_finding.confidence or "low"
                result["evidence_quality"] = "medium"

    elif norm_type == "weak_ssh_configuration":
        result["normalized_category"] = "weak_cryptography"
        result["root_cause"] = "insecure_configuration"
        result["impact"] = "authentication_bypass"
        result["remediation"] = "Harden SSH configuration and disable weak or unnecessary protocols, algorithms, and authentication settings."
        result["confidence"] = raw_finding.confidence or "medium"
        result["evidence_quality"] = "medium"

    return result
