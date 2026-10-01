from typing import List, Dict, Any

REMEDIATION_CATALOG: List[Dict[str, Any]] = [
    {
        "normalized_type": "missing_security_headers",
        "title": "Configure HTTP Security Headers",
        "summary": "Configure appropriate HTTP security headers to reduce common browser-side security risks and information exposure.",
        "detailed_guidance": "Configure the web server or application to emit appropriate security headers based on the application's requirements. At minimum, review headers such as Strict-Transport-Security, X-Content-Type-Options, Content-Security-Policy, Referrer-Policy, and appropriate framing protection. Avoid blindly enabling headers without validating application compatibility.",
        "remediation_type": "configuration",
        "priority": "high",
        "verification_guidance": "Repeat the HTTP security-header assessment and confirm that the required security headers are present with appropriate values on the affected endpoint.",
        "rationale": "The finding indicates that expected HTTP security controls are missing from the affected web application.",
        "mapping_confidence": "high"
    },
    {
        "normalized_type": "exposed_service",
        "title": "Restrict or Disable Unnecessary Network Service",
        "summary": "Disable unnecessary exposed services or restrict access to trusted networks and hosts.",
        "detailed_guidance": "Determine whether the exposed service is required. If it is not required, disable it. If it is required, restrict network access using appropriate firewall rules, network segmentation, access controls, or trusted source ranges. Ensure that exposed services are appropriately hardened and patched.",
        "remediation_type": "network",
        "priority": "medium",
        "verification_guidance": "Repeat the network-service assessment and confirm that the unnecessary service is no longer exposed or that access is restricted according to the intended security policy.",
        "rationale": "The finding represents a network service that is reachable from the assessed scope.",
        "mapping_confidence": "high"
    },
    {
        "normalized_type": "sql_injection",
        "title": "Use Parameterized Database Queries",
        "summary": "Prevent SQL injection by using parameterized queries or prepared statements for database operations.",
        "detailed_guidance": "Use parameterized queries, prepared statements, or an equivalent safe database abstraction for all user-controlled values. Do not construct SQL statements by concatenating or interpolating untrusted input. Apply appropriate input validation as an additional control, but do not rely on validation alone to prevent SQL injection.",
        "remediation_type": "code",
        "priority": "critical",
        "verification_guidance": "Repeat the relevant SQL injection test against the affected parameter and confirm that the previously observed injection behavior is no longer reproducible.",
        "rationale": "The finding indicates that untrusted input can influence database query execution.",
        "mapping_confidence": "high"
    },
    {
        "normalized_type": "cross_site_scripting",
        "title": "Implement Context-Aware Output Encoding",
        "summary": "Prevent cross-site scripting by safely handling untrusted input and encoding output according to its execution context.",
        "detailed_guidance": "Apply context-appropriate output encoding and safely handle untrusted input before rendering it in HTML, JavaScript, CSS, URLs, or other interpreted contexts. Use framework-provided escaping mechanisms where available. Avoid unsafe DOM APIs and evaluate whether a restrictive Content Security Policy can provide additional defense in depth.",
        "remediation_type": "code",
        "priority": "high",
        "verification_guidance": "Repeat the relevant XSS test and confirm that the previously observed payload is no longer executed or reflected in an executable context.",
        "rationale": "The finding indicates that attacker-controlled input can reach a browser execution context without sufficient protection.",
        "mapping_confidence": "high"
    },
    {
        "normalized_type": "weak_ssh_configuration",
        "title": "Harden SSH Configuration",
        "summary": "Harden SSH configuration and disable unnecessary or weak authentication and cryptographic options.",
        "detailed_guidance": "Review the SSH server configuration and disable deprecated or unnecessary protocols, ciphers, MACs, key-exchange algorithms, authentication methods, and other insecure options. Prefer current cryptographic algorithms and strong authentication. Restrict SSH exposure to trusted networks where possible and keep the SSH implementation patched.",
        "remediation_type": "configuration",
        "priority": "high",
        "verification_guidance": "Repeat the SSH configuration assessment and confirm that weak or deprecated configuration options are no longer exposed.",
        "rationale": "The finding indicates that the SSH service uses a configuration that should be hardened.",
        "mapping_confidence": "high"
    }
]
