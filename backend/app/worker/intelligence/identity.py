import json
import hashlib
from typing import Dict, Any
from app.models.assessment import Finding as DbFinding

def build_identity_payload(assessment_id: int, normalized_type: str, db_finding: DbFinding) -> Dict[str, Any]:
    """
    Builds the canonical identity payload.
    Extracts relevant attack-surface context directly from the db_finding relationships.
    """
    payload = {
        "assessment_id": assessment_id,
        "normalized_type": normalized_type
    }

    if db_finding.web_endpoint:
        payload["hostname"] = db_finding.web_endpoint.web_application.hostname
        payload["port"] = db_finding.web_endpoint.web_application.port
        payload["path"] = db_finding.web_endpoint.path
        payload["method"] = db_finding.web_endpoint.method
    elif db_finding.web_application:
        payload["hostname"] = db_finding.web_application.hostname
        payload["port"] = db_finding.web_application.port
    elif db_finding.network_service:
        payload["ip_address"] = db_finding.network_service.asset.ip_address
        payload["port"] = db_finding.network_service.port
        payload["protocol"] = db_finding.network_service.protocol
    elif db_finding.asset:
        payload["ip_address"] = db_finding.asset.ip_address
    elif db_finding.location:
        payload["location"] = db_finding.location

    return payload

def compute_identity_hash(payload: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 hash from the canonical payload.
    """
    canonical_string = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()
