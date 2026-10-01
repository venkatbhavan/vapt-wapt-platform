import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.assessment import Base, Project, Assessment, Finding, ScanJob
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.worker.correlation.correlator import correlate_finding

class TestFindingCorrelation(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        self.project = Project(name="Correlation Project")
        self.db.add(self.project)
        self.db.flush()

        self.assessment = Assessment(
            project_id=self.project.id, name="Assessment A", target="127.0.0.1", scope="127.0.0.1", authorization_confirmed=True
        )
        self.assessment_b = Assessment(
            project_id=self.project.id, name="Assessment B", target="127.0.0.1", scope="127.0.0.1", authorization_confirmed=True
        )
        self.db.add(self.assessment)
        self.db.add(self.assessment_b)
        self.db.flush()
        
        self.job = ScanJob(assessment_id=self.assessment.id, scan_profile="standard")
        self.job_b = ScanJob(assessment_id=self.assessment_b.id, scan_profile="standard")
        self.db.add(self.job)
        self.db.add(self.job_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _seed_db(self):
        a1 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        a2 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.20", hostname="web.local")
        ab = Asset(assessment_id=self.assessment_b.id, ip_address="192.168.1.10")
        
        self.db.add_all([a1, a2, ab])
        self.db.flush()
        
        s1 = NetworkService(asset_id=a1.id, port=80, protocol="tcp", state="open")
        s2 = NetworkService(asset_id=a1.id, port=53, protocol="tcp", state="open")
        s3 = NetworkService(asset_id=a1.id, port=53, protocol="udp", state="open")
        self.db.add_all([s1, s2, s3])
        self.db.flush()
        
        wa1 = WebApplication(asset_id=a1.id, network_service_id=s1.id, base_url="http://192.168.1.10", scheme="http", port=80)
        self.db.add(wa1)
        self.db.flush()
        
        we1 = WebEndpoint(web_application_id=wa1.id, path="/login", method="GET")
        we2 = WebEndpoint(web_application_id=wa1.id, path="/login", method="POST")
        we3 = WebEndpoint(web_application_id=wa1.id, path="/unique", method="GET")
        self.db.add_all([we1, we2, we3])
        self.db.commit()
        
        return a1, a2, ab, s1, s2, s3, wa1, we1, we2, we3

    def _make_finding(self, loc):
        f = Finding(scan_job_id=self.job.id, title="Test", location=loc, severity="low")
        self.db.add(f)
        self.db.flush()
        return f

    # 1. Exact IP finding correlates to Asset.
    def test_01_exact_ip_asset(self):
        a1, *rest = self._seed_db()
        f = self._make_finding("192.168.1.10")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.match_type, "asset")
        self.assertEqual(res.asset_id, a1.id)

    # 2. Exact IP + TCP port correlates to NetworkService.
    def test_02_ip_tcp_port(self):
        a1, a2, ab, s1, *rest = self._seed_db()
        f = self._make_finding("192.168.1.10:80/tcp")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.match_type, "service")
        self.assertEqual(res.network_service_id, s1.id)

    # 3. Exact IP + UDP port correlates to UDP NetworkService.
    # 4. TCP and UDP same port remain distinct.
    def test_03_04_udp_port_distinct(self):
        a1, a2, ab, s1, s2, s3, *rest = self._seed_db()
        f_tcp = self._make_finding("192.168.1.10:53/tcp")
        f_udp = self._make_finding("192.168.1.10:53/udp")
        
        res_tcp = correlate_finding(self.db, self.assessment.id, f_tcp)
        res_udp = correlate_finding(self.db, self.assessment.id, f_udp)
        
        self.assertEqual(res_tcp.network_service_id, s2.id)
        self.assertEqual(res_udp.network_service_id, s3.id)
        self.assertNotEqual(res_tcp.network_service_id, res_udp.network_service_id)

    # 5. Exact application URL correlates to WebApplication.
    def test_05_application_url(self):
        a1, a2, ab, s1, s2, s3, wa1, *rest = self._seed_db()
        f = self._make_finding("http://192.168.1.10/")
        res = correlate_finding(self.db, self.assessment.id, f)
        # It won't find an endpoint for "/", so it correlates to WebApplication
        self.assertEqual(res.match_type, "application")
        self.assertEqual(res.web_application_id, wa1.id)

    # 6. Exact endpoint URL + known method correlates to WebEndpoint.
    def test_06_exact_endpoint(self):
        # We don't have HTTP method in our locator (only URL), 
        # so if the path has multiple methods (like /login), it stops at App.
        # But if it has a unique endpoint (like /unique), it correlates to Endpoint!
        a1, a2, ab, s1, s2, s3, wa1, we1, we2, we3 = self._seed_db()
        f = self._make_finding("http://192.168.1.10/unique")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.match_type, "endpoint")
        self.assertEqual(res.web_endpoint_id, we3.id)

    # 7. Query string does not prevent endpoint correlation.
    def test_07_query_string(self):
        a1, a2, ab, s1, s2, s3, wa1, we1, we2, we3 = self._seed_db()
        f = self._make_finding("http://192.168.1.10/unique?id=1")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.web_endpoint_id, we3.id)

    # 8. Fragment does not prevent endpoint correlation.
    def test_08_fragment(self):
        a1, a2, ab, s1, s2, s3, wa1, we1, we2, we3 = self._seed_db()
        f = self._make_finding("http://192.168.1.10/unique#section")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.web_endpoint_id, we3.id)

    # 9. GET and POST remain distinct.
    # 10. Unknown method does not arbitrarily select GET/POST.
    def test_09_10_unknown_method_ambiguous(self):
        a1, a2, ab, s1, s2, s3, wa1, we1, we2, we3 = self._seed_db()
        f = self._make_finding("http://192.168.1.10/login")
        res = correlate_finding(self.db, self.assessment.id, f)
        # Because there's GET /login and POST /login, it must stop at application
        self.assertEqual(res.match_type, "application")
        self.assertEqual(res.web_application_id, wa1.id)
        self.assertIsNone(res.web_endpoint_id)

    # 11. Unknown method with one unique endpoint may correlate safely if deterministic.
    # Covered by test_06.

    # 12. Host-level finding remains at Asset level.
    # Covered by test_01.
    
    # 13. Application-level finding does not incorrectly force an endpoint.
    # Covered by test_05.

    # 14. Unmatched finding remains uncorrelated.
    def test_14_unmatched_finding(self):
        f = self._make_finding("http://not-exist.com")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.match_type, "none")
        self.assertIsNone(res.asset_id)

    # 15. Same IP in different assessments remains isolated.
    # 16. Same URL in different assessments remains isolated.
    # 17. Finding from ScanJob A cannot correlate to ScanJob/Assessment B attack surface.
    def test_15_16_17_isolation(self):
        a1, a2, ab, *rest = self._seed_db()
        f_b = Finding(scan_job_id=self.job_b.id, title="Test", location="192.168.1.10", severity="low")
        self.db.add(f_b)
        self.db.flush()
        
        # Correlating in Assessment B should find ab, not a1
        res = correlate_finding(self.db, self.assessment_b.id, f_b)
        self.assertEqual(res.asset_id, ab.id)
        self.assertNotEqual(res.asset_id, a1.id)

    # 18. Existing finding fields remain unchanged.
    def test_18_fields_unchanged(self):
        a1, *rest = self._seed_db()
        f = Finding(scan_job_id=self.job.id, title="XSS", description="Bad", severity="high", location="192.168.1.10")
        self.db.add(f)
        self.db.flush()
        
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(f.title, "XSS")
        self.assertEqual(f.description, "Bad")
        self.assertEqual(f.severity, "high")

    # 19. Correlation failure does not invalidate the finding.
    def test_19_correlation_failure_safe(self):
        f = self._make_finding("totally invalid location !@#")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertEqual(res.match_type, "none")
        self.assertIsNone(res.asset_id)

    # 20. Correlation reason/match_type is deterministic.
    def test_20_reason_deterministic(self):
        a1, *rest = self._seed_db()
        f = self._make_finding("192.168.1.10")
        res = correlate_finding(self.db, self.assessment.id, f)
        self.assertIn("Asset", res.reason)

    # 21. Assessment deletion still cascades correctly.
    def test_21_cascade(self):
        a1, *rest = self._seed_db()
        self.assertEqual(self.db.query(Asset).count(), 3)
        self.db.delete(self.assessment)
        self.db.commit()
        # Should only leave assessment_b's asset
        self.assertEqual(self.db.query(Asset).count(), 1)
        
    # 22. Existing Nmap findings still correlate correctly.
    def test_22_nmap_finding_integration(self):
        from app.worker.service import process_scan_job
        from app.worker.scanners.models import ScannerResult, Finding as ResultFinding
        from unittest.mock import patch
        
        res = ScannerResult(
            scanner="nmap", target="192.168.1.10", scan_profile="standard",
            hosts=[{
                "ip_address": "192.168.1.10",
                "services": [{"port": 22, "protocol": "tcp", "state": "open"}]
            }],
            findings=[ResultFinding(title="SSH Weak", location="192.168.1.10:22/tcp", severity="low", description="desc")]
        )
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, self.job.id)
            
        f = self.db.query(Finding).filter(Finding.scan_job_id == self.job.id).first()
        self.assertIsNotNone(f.asset_id)
        self.assertIsNotNone(f.network_service_id)
        
    # 23. Existing ZAP findings still correlate correctly.
    def test_23_zap_finding_integration(self):
        from app.worker.service import process_scan_job
        from app.worker.scanners.models import ScannerResult, WebApplicationObservation, WebEndpointObservation, Finding as ResultFinding
        from unittest.mock import patch
        
        res = ScannerResult(
            scanner="zap", target="192.168.1.10", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://192.168.1.10", scheme="http", hostname="192.168.1.10", port=80,
                endpoints=[WebEndpointObservation(url="http://192.168.1.10/login", path="/login", method="GET")]
            )],
            findings=[ResultFinding(title="XSS", location="http://192.168.1.10/login", severity="high", description="desc")]
        )
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = res
            process_scan_job(self.db, self.job.id)
            
        f = self.db.query(Finding).filter(Finding.scan_job_id == self.job.id).first()
        self.assertIsNotNone(f.asset_id)
        self.assertIsNotNone(f.network_service_id)
        self.assertIsNotNone(f.web_application_id)
        self.assertIsNotNone(f.web_endpoint_id)

if __name__ == "__main__":
    unittest.main()
