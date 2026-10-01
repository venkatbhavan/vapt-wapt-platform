from typing import List, Dict, Any

COMPLIANCE_MAPPING_CATALOG: List[Dict[str, Any]] = [
    # OWASP Top 10:2021 Mappings
    {
        "framework_name": "OWASP Top 10",
        "framework_version": "2021",
        "control_id": "A03:2021",
        "control_title": "Injection",
        "normalized_type": "sql_injection",
        "mapping_type": "direct",
        "mapping_confidence": "high",
        "rationale": "SQL injection is an injection vulnerability and is directly covered by the OWASP Top 10:2021 Injection category.",
        "source": "OWASP Top 10:2021 — A03:2021 Injection"
    },
    {
        "framework_name": "OWASP Top 10",
        "framework_version": "2021",
        "control_id": "A03:2021",
        "control_title": "Injection",
        "normalized_type": "cross_site_scripting",
        "mapping_type": "direct",
        "mapping_confidence": "high",
        "rationale": "Cross-site scripting is categorized as an injection vulnerability and is directly covered by the OWASP Top 10:2021 Injection category.",
        "source": "OWASP Top 10:2021 — A03:2021 Injection"
    },
    {
        "framework_name": "OWASP Top 10",
        "framework_version": "2021",
        "control_id": "A05:2021",
        "control_title": "Security Misconfiguration",
        "normalized_type": "missing_security_headers",
        "mapping_type": "direct",
        "mapping_confidence": "high",
        "rationale": "Missing or incorrectly configured HTTP security headers are addressed under OWASP Top 10:2021 Security Misconfiguration.",
        "source": "OWASP Top 10:2021 — A05:2021 Security Misconfiguration"
    },
    {
        "framework_name": "OWASP Top 10",
        "framework_version": "2021",
        "control_id": "A05:2021",
        "control_title": "Security Misconfiguration",
        "normalized_type": "exposed_service",
        "mapping_type": "related",
        "mapping_confidence": "medium",
        "rationale": "An unnecessarily exposed service can represent a security misconfiguration. This is a related OWASP Top 10:2021 Security Misconfiguration concern rather than a one-to-one vulnerability classification.",
        "source": "OWASP Top 10:2021 — A05:2021 Security Misconfiguration"
    },

    # NIST CSF 2.0 Mappings
    {
        "framework_name": "NIST Cybersecurity Framework",
        "framework_version": "2.0",
        "control_id": "PR.PS-01",
        "control_title": "Configuration management practices are established and applied",
        "normalized_type": "missing_security_headers",
        "mapping_type": "related",
        "mapping_confidence": "medium",
        "rationale": "Missing security headers can indicate that secure configuration practices for a web application or web server are not fully established or applied.",
        "source": "NIST CSF 2.0 — PR.PS-01"
    },
    {
        "framework_name": "NIST Cybersecurity Framework",
        "framework_version": "2.0",
        "control_id": "PR.PS-01",
        "control_title": "Configuration management practices are established and applied",
        "normalized_type": "exposed_service",
        "mapping_type": "related",
        "mapping_confidence": "medium",
        "rationale": "An unnecessarily exposed service can indicate that secure configuration and hardened configuration practices are not fully established or applied.",
        "source": "NIST CSF 2.0 — PR.PS-01"
    },
    {
        "framework_name": "NIST Cybersecurity Framework",
        "framework_version": "2.0",
        "control_id": "PR.PS-01",
        "control_title": "Configuration management practices are established and applied",
        "normalized_type": "weak_ssh_configuration",
        "mapping_type": "related",
        "mapping_confidence": "medium",
        "rationale": "Weak SSH configuration can indicate that hardened configuration practices are not fully established or applied.",
        "source": "NIST CSF 2.0 — PR.PS-01"
    }
]
