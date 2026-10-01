import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus, Finding as DbFinding, Evidence as DbEvidence
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.worker.service import process_scan_job
from app.worker.scanners.models import ScannerResult, Finding as ScannerFinding, WebApplicationObservation, WebEndpointObservation, HostObservation, ServiceObservation, EvidenceItem

class TestFindingDeduplication(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db = self.SessionLocal()

        project = Project(name="Test Project", description="Test")
        self.db.add(project)
        self.db.flush()

        self.assessment = Assessment(name="Test Assessment", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        self.db.add(self.assessment)
        self.db.flush()

        self.assessment_b = Assessment(name="Test Assessment B", project_id=project.id, target="127.0.0.1", scope="local", authorization_confirmed=True)
        self.db.add(self.assessment_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _run_job(self, res: ScannerResult, assessment_id=None):
        aid = assessment_id or self.assessment.id
        job = ScanJob(assessment_id=aid, scan_profile="standard")
        self.db.add(job)
        self.db.commit()

        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, job.id)

        self.db.refresh(job)
        return job

    def test_a_duplicate_scan_merge(self):
        # A. Same finding + same endpoint + two scan jobs -> 1 Finding, 2 Evidence records
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[ScannerFinding(title="XSS Found", severity="high", description="XSS", location="http://127.0.0.1/api", evidence=[EvidenceItem(evidence_type="text", content="proof1")])],
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1", scheme="http", hostname="127.0.0.1", port=80, endpoints=[WebEndpointObservation(url="http://127.0.0.1/api", path="/api", method="GET")])]
        )
        self._run_job(res)
        self._run_job(res)

        findings = self.db.query(DbFinding).all()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].scanner_sources, ["zap"])

        evidence = self.db.query(DbEvidence).filter(DbEvidence.finding_id == findings[0].id).all()
        self.assertEqual(len(evidence), 2)

    def test_b_same_issue_different_endpoint(self):
        # B. Same finding type + different endpoint -> 2 Findings
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[
                ScannerFinding(title="XSS Found", severity="high", description="XSS", location="http://127.0.0.1/api"),
                ScannerFinding(title="XSS Found", severity="high", description="XSS", location="http://127.0.0.1/admin")
            ],
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1", scheme="http", hostname="127.0.0.1", port=80, endpoints=[
                WebEndpointObservation(url="http://127.0.0.1/api", path="/api", method="GET"),
                WebEndpointObservation(url="http://127.0.0.1/admin", path="/admin", method="GET")
            ])]
        )
        self._run_job(res)
        self.assertEqual(self.db.query(DbFinding).count(), 2)

    def test_c_same_issue_different_port(self):
        # C. Same finding type + different port -> 2 Findings
        res = ScannerResult(
            scanner="nmap", target="127.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="127.0.0.1", services=[
                ServiceObservation(port=80, protocol="tcp", state="open"),
                ServiceObservation(port=443, protocol="tcp", state="open")
            ])],
            findings=[
                ScannerFinding(title="Open Port", severity="info", description="Port 80", location="127.0.0.1:80/tcp"),
                ScannerFinding(title="Open Port", severity="info", description="Port 443", location="127.0.0.1:443/tcp")
            ]
        )
        self._run_job(res)
        self.assertEqual(self.db.query(DbFinding).count(), 2)

    def test_d_same_endpoint_different_method(self):
        # D. Same endpoint + GET vs POST -> 2 Findings
        # Note: The correlator only parses URL paths natively. If we mock two findings already assigned to distinct WebEndpoint IDs,
        # we bypass the correlator's string parsing and test the identity generation.
        # Instead, we test that the identity builder includes the method.
        from app.models.assessment import Finding
        from app.models.attack_surface import WebEndpoint, WebApplication
        from app.worker.intelligence.identity import build_identity_payload, compute_identity_hash
        app = WebApplication(hostname="127.0.0.1", port=80, base_url="http://127.0.0.1")
        ep_get = WebEndpoint(web_application=app, path="/api", method="GET")
        ep_post = WebEndpoint(web_application=app, path="/api", method="POST")

        f_get = Finding(web_endpoint=ep_get)
        f_post = Finding(web_endpoint=ep_post)

        h1 = compute_identity_hash(build_identity_payload(1, "xss", f_get))
        h2 = compute_identity_hash(build_identity_payload(1, "xss", f_post))
        self.assertNotEqual(h1, h2)

    def test_e_assessment_isolation(self):
        # E. Same finding + same endpoint + different assessments -> 2 Findings
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[ScannerFinding(title="XSS Found", severity="high", description="XSS", location="http://127.0.0.1/api")],
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1", scheme="http", hostname="127.0.0.1", port=80, endpoints=[WebEndpointObservation(url="http://127.0.0.1/api", path="/api", method="GET")])]
        )
        self._run_job(res, assessment_id=self.assessment.id)
        self._run_job(res, assessment_id=self.assessment_b.id)

        findings = self.db.query(DbFinding).all()
        self.assertEqual(len(findings), 2)

    def test_f_scanner_sources_merge(self):
        # F. Same identity reported by Nmap and ZAP -> 1 Finding, scanner_sources: ["nmap", "zap"]
        res_nmap = ScannerResult(
            scanner="nmap", target="127.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="127.0.0.1", services=[ServiceObservation(port=80, protocol="tcp", state="open")])],
            findings=[ScannerFinding(title="Open Port 80", severity="info", description="Open", location="127.0.0.1:80/tcp")]
        )
        self._run_job(res_nmap)

        res_zap = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[ScannerFinding(title="Open Port 80", severity="info", description="Open via ZAP", location="127.0.0.1:80/tcp")]
        )
        self._run_job(res_zap)

        findings = self.db.query(DbFinding).all()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].scanner_sources, ["nmap", "zap"])

    def test_g_h_i_j_merge_semantics(self):
        # Tests G, H, I, J inside one integrated flow:
        # Initial Finding with specific manual overrides / scanner values
        res1 = ScannerResult(
            scanner="nmap", target="127.0.0.1", scan_profile="standard",
            hosts=[HostObservation(ip_address="127.0.0.1", services=[ServiceObservation(port=80, protocol="tcp", state="open")])],
            findings=[ScannerFinding(title="Open Port 80", severity="medium", description="Open", location="127.0.0.1:80/tcp", confidence="medium", evidence=[EvidenceItem(evidence_type="text", content="proof1")])]
        )
        self._run_job(res1)

        # We manually modify the finding in DB to simulate user overrides or risk engine overrides
        f = self.db.query(DbFinding).first()
        f.severity = "high"
        f.confidence = "medium"
        f.risk_score = 9.9
        f.risk_level = "critical"
        f.risk_rationale = "Custom rationale"
        self.db.commit()

        # Second scan from ZAP tries to report the SAME issue with 'high' confidence, 'info' severity
        res2 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[ScannerFinding(title="Open Port 80", severity="info", description="Open via ZAP", location="127.0.0.1:80/tcp", confidence="high", evidence=[EvidenceItem(evidence_type="text", content="proof2")])]
        )
        self._run_job(res2)

        f2 = self.db.query(DbFinding).first()
        # Verify H: Existing severity is preserved (doesn't become info or high)
        self.assertEqual(f2.severity, "high")
        # Verify I: Existing confidence is preserved
        self.assertEqual(f2.confidence, "medium")
        # Verify J: Existing risk score/level/rationale preserved
        self.assertEqual(f2.risk_score, 9.9)
        self.assertEqual(f2.risk_level, "critical")
        self.assertEqual(f2.risk_rationale, "Custom rationale")
        # Verify G: Evidence is preserved (1 from res1, 1 from res2)
        self.assertEqual(len(f2.evidence_list), 2)

if __name__ == "__main__":
    unittest.main()
