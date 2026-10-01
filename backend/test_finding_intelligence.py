import unittest
from app.worker.intelligence.normalizer import normalize_finding
from app.worker.intelligence.identity import build_identity_payload, compute_identity_hash
from app.worker.scanners.models import Finding as ScannerFinding, EvidenceItem
from app.models.assessment import Finding

class TestFindingIntelligence(unittest.TestCase):

    def test_normalization_known_types(self):
        f = ScannerFinding(title="Open Port 80", severity="info", description="Port is open")
        norm = normalize_finding("nmap", f)
        self.assertEqual(norm["normalized_category"], "network_exposure")
        self.assertEqual(norm["normalized_type"], "exposed_service")
        self.assertEqual(norm["root_cause"], "insecure_configuration")
        self.assertEqual(norm["impact"], "network_exposure")
        self.assertEqual(norm["evidence_quality"], "high")
        self.assertEqual(norm["confidence"], "high")

    def test_normalization_unknown(self):
        f = ScannerFinding(title="Weird Issue", severity="low", description="Desc", remediation="Do fix", impact="bad")
        norm = normalize_finding("zap", f)
        self.assertEqual(norm["normalized_category"], "unknown")
        self.assertEqual(norm["normalized_type"], "unknown")
        self.assertEqual(norm["root_cause"], None)
        self.assertEqual(norm["impact"], "bad")
        self.assertEqual(norm["remediation"], "Do fix")
        self.assertEqual(norm["evidence_quality"], "low")

    def test_canonical_identity_generation(self):
        f = Finding(title="Test")
        payload = build_identity_payload(1, "unknown", f)
        self.assertEqual(payload, {"assessment_id": 1, "normalized_type": "unknown"})

    def test_deterministic_hash_sorting(self):
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        self.assertEqual(compute_identity_hash(payload1), compute_identity_hash(payload2))

    def test_confidence_and_evidence_quality_rules(self):
        f = ScannerFinding(title="XSS Found", severity="high", description="XSS")
        norm_no_proof = normalize_finding("zap", f)
        self.assertEqual(norm_no_proof["confidence"], "low")
        self.assertEqual(norm_no_proof["evidence_quality"], "medium")

        f_proof = ScannerFinding(title="XSS Found", severity="high", description="XSS", evidence=[EvidenceItem(evidence_type="text", content="<script>")])
        norm_proof = normalize_finding("zap", f_proof)
        self.assertEqual(norm_proof["confidence"], "high")
        self.assertEqual(norm_proof["evidence_quality"], "high")

    def test_root_cause_impact_remediation_mappings(self):
        f = ScannerFinding(title="SQL Injection", severity="high", description="SQLi")
        norm = normalize_finding("zap", f)
        self.assertEqual(norm["root_cause"], "improper_input_validation")
        self.assertEqual(norm["impact"], "confidentiality_integrity_availability_compromise")
        self.assertIn("parameterized queries", norm["remediation"])

        f_headers = ScannerFinding(title="Missing Security Headers", severity="low", description="Desc")
        norm_headers = normalize_finding("zap", f_headers)
        self.assertEqual(norm_headers["normalized_category"], "security_misconfiguration")
        self.assertEqual(norm_headers["normalized_type"], "missing_security_headers")
        self.assertEqual(norm_headers["root_cause"], "missing_security_control")
        self.assertEqual(norm_headers["impact"], "information_disclosure")

        f_ssh = ScannerFinding(title="SSH Weak MAC", severity="medium", description="Desc")
        norm_ssh = normalize_finding("nmap", f_ssh)
        self.assertEqual(norm_ssh["normalized_category"], "weak_cryptography")
        self.assertEqual(norm_ssh["normalized_type"], "weak_ssh_configuration")
        self.assertEqual(norm_ssh["root_cause"], "insecure_configuration")
        self.assertEqual(norm_ssh["impact"], "authentication_bypass")

if __name__ == '__main__':
    unittest.main()
