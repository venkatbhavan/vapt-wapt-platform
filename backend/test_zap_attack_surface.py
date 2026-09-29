import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.models.assessment import Base, Project, Assessment, ScanJob, ScanJobStatus
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.worker.scanners.models import ScannerResult, WebApplicationObservation, WebEndpointObservation, Finding
from app.worker.service import process_scan_job
from app.worker.scanners.zap_parser import normalize_url

class TestZapAttackSurfaceIngestion(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        self.project = Project(name="ZAP Ingestion Project")
        self.db.add(self.project)
        self.db.flush()

        self.assessment = Assessment(
            project_id=self.project.id,
            name="Assessment A",
            target="127.0.0.1",
            scope="127.0.0.1",
            authorization_confirmed=True
        )
        self.db.add(self.assessment)
        
        self.assessment_b = Assessment(
            project_id=self.project.id,
            name="Assessment B",
            target="127.0.0.1",
            scope="127.0.0.1",
            authorization_confirmed=True
        )
        self.db.add(self.assessment_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        
    def _run_zap_job(self, result: ScannerResult, assessment_id: int = None):
        if assessment_id is None:
            assessment_id = self.assessment.id
        job = ScanJob(assessment_id=assessment_id, scan_profile="standard")
        self.db.add(job)
        self.db.commit()
        
        with patch("app.worker.service.get_scanner") as mock:
            mock.return_value.scan.return_value = result
            return process_scan_job(self.db, job.id)

    # 1. One URL creates one Asset.
    def test_01_one_url_creates_one_asset(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res)
        self.assertEqual(self.db.query(Asset).count(), 1)
        self.assertEqual(self.db.query(Asset).first().ip_address, "127.0.0.1")

    # 2. One URL creates one NetworkService.
    def test_02_one_url_creates_one_network_service(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res)
        self.assertEqual(self.db.query(NetworkService).count(), 1)
        
    # 3. One base URL creates one WebApplication.
    def test_03_one_base_url_creates_one_web_application(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res)
        self.assertEqual(self.db.query(WebApplication).count(), 1)
        self.assertEqual(self.db.query(WebApplication).first().base_url, "http://127.0.0.1:80")

    # 4. Multiple paths create multiple WebEndpoints.
    # 5. Multiple paths under the same host/port reuse the same WebApplication.
    def test_04_05_multiple_paths_endpoints_reuse_app(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[
                    WebEndpointObservation(url="http://127.0.0.1/login", path="/login", method="GET"),
                    WebEndpointObservation(url="http://127.0.0.1/api", path="/api", method="GET")
                ]
            )]
        )
        self._run_zap_job(res)
        self.assertEqual(self.db.query(WebApplication).count(), 1)
        self.assertEqual(self.db.query(WebEndpoint).count(), 2)
        paths = {e.path for e in self.db.query(WebEndpoint).all()}
        self.assertEqual(paths, {"/login", "/api"})

    # 6. Query strings do not create duplicate endpoints.
    def test_06_query_strings_normalized(self):
        # We test normalize_url manually since ingestion relies on it
        n1 = normalize_url("http://test.local/api?id=1", "GET")
        n2 = normalize_url("http://test.local/api?id=2", "GET")
        self.assertEqual(n1, n2)
        self.assertEqual(n1[4], "/api")

    # 7. URL fragments do not create duplicate endpoints.
    def test_07_fragments_normalized(self):
        n1 = normalize_url("http://test.local/api#section1", "GET")
        n2 = normalize_url("http://test.local/api#section2", "GET")
        self.assertEqual(n1, n2)
        self.assertEqual(n1[4], "/api")

    # 8. GET /login and POST /login are distinct endpoints.
    def test_08_methods_are_distinct(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[
                    WebEndpointObservation(url="http://127.0.0.1/login", path="/login", method="GET"),
                    WebEndpointObservation(url="http://127.0.0.1/login", path="/login", method="POST")
                ]
            )]
        )
        self._run_zap_job(res)
        eps = self.db.query(WebEndpoint).all()
        self.assertEqual(len(eps), 2)
        methods = {e.method for e in eps}
        self.assertEqual(methods, {"GET", "POST"})

    # 9. HTTP and HTTPS applications are correctly distinguished.
    def test_09_http_https_distinct(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[
                WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80),
                WebApplicationObservation(base_url="https://127.0.0.1:443", scheme="https", hostname="127.0.0.1", port=443)
            ]
        )
        self._run_zap_job(res)
        self.assertEqual(self.db.query(WebApplication).count(), 2)

    # 10. Explicit/non-default ports are preserved correctly.
    def test_10_explicit_ports(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:3000", scheme="http", hostname="127.0.0.1", port=3000)]
        )
        self._run_zap_job(res)
        app = self.db.query(WebApplication).first()
        self.assertEqual(app.port, 3000)
        self.assertEqual(app.base_url, "http://127.0.0.1:3000")

    # 11. Re-ingesting the same ZAP result is idempotent.
    def test_11_idempotency(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[WebEndpointObservation(url="http://127.0.0.1/", path="/", method="GET")]
            )]
        )
        self._run_zap_job(res)
        self._run_zap_job(res)
        
        self.assertEqual(self.db.query(Asset).count(), 1)
        self.assertEqual(self.db.query(NetworkService).count(), 1)
        self.assertEqual(self.db.query(WebApplication).count(), 1)
        self.assertEqual(self.db.query(WebEndpoint).count(), 1)

    # 12. Later scan adds only new endpoints.
    def test_12_later_scan_adds_new_endpoints(self):
        res1 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[WebEndpointObservation(url="http://127.0.0.1/", path="/", method="GET")]
            )]
        )
        res2 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[
                    WebEndpointObservation(url="http://127.0.0.1/", path="/", method="GET"),
                    WebEndpointObservation(url="http://127.0.0.1/admin", path="/admin", method="GET")
                ]
            )]
        )
        self._run_zap_job(res1)
        self._run_zap_job(res2)
        
        self.assertEqual(self.db.query(WebApplication).count(), 1)
        self.assertEqual(self.db.query(WebEndpoint).count(), 2)

    # 13. Later scan enriches application metadata.
    # 14. Useful existing metadata is not overwritten with None/empty values.
    def test_13_14_metadata_enrichment_no_none_overwrite(self):
        res1 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80, title="Initial", tech_info="Node"
            )]
        )
        res2 = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80, title="Better Title", tech_info=None
            )]
        )
        self._run_zap_job(res1)
        self._run_zap_job(res2)
        
        app = self.db.query(WebApplication).first()
        self.assertEqual(app.title, "Better Title")
        self.assertEqual(app.tech_info, "Node")

    # 15. ZAP can create an Asset if Nmap has not run first.
    # 16. ZAP can create a NetworkService when the port is known.
    def test_15_16_zap_creates_parents_if_missing(self):
        self.assertEqual(self.db.query(Asset).count(), 0)
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://10.0.0.99:80", scheme="http", hostname="10.0.0.99", port=80)]
        )
        self._run_zap_job(res)
        
        asset = self.db.query(Asset).first()
        self.assertEqual(asset.ip_address, "10.0.0.99")
        svc = self.db.query(NetworkService).first()
        self.assertEqual(svc.port, 80)
        self.assertEqual(svc.protocol, "tcp")

    # 17. Same IP in different assessments remains isolated.
    def test_17_assessment_isolation(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res, assessment_id=self.assessment.id)
        self._run_zap_job(res, assessment_id=self.assessment_b.id)
        
        self.assertEqual(self.db.query(WebApplication).count(), 2)
        self.assertEqual(self.db.query(Asset).count(), 2)

    # 18. Existing ZAP findings still persist.
    # 19. Risk calculation still works.
    def test_18_19_findings_and_risk(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[Finding(title="XSS", severity="high", description="XSS Found", confidence="high")],
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        self._run_zap_job(res)
        
        from app.models.assessment import Finding as DbFinding
        f = self.db.query(DbFinding).first()
        self.assertEqual(f.title, "XSS")
        self.assertEqual(f.severity, "high")
        self.assertIsNotNone(f.risk_score)

    # 20. Transaction rollback works if attack-surface ingestion fails.
    def test_20_transaction_rollback(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            findings=[Finding(title="Will Rollback", severity="low", description="Desc")],
            web_applications=[WebApplicationObservation(base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80)]
        )
        with patch("app.models.attack_surface.WebApplication", side_effect=Exception("Crash during ZAP flush")):
            job = self._run_zap_job(res)
            
        self.assertEqual(job.status, ScanJobStatus.failed)
        
        from app.models.assessment import Finding as DbFinding
        self.assertEqual(self.db.query(DbFinding).count(), 0)
        self.assertEqual(self.db.query(WebApplication).count(), 0)

    # 21. Assessment deletion cascades through: Asset -> NetworkService -> WebApplication -> WebEndpoint.
    def test_21_cascade_deletion(self):
        res = ScannerResult(
            scanner="zap", target="127.0.0.1", scan_profile="standard",
            web_applications=[WebApplicationObservation(
                base_url="http://127.0.0.1:80", scheme="http", hostname="127.0.0.1", port=80,
                endpoints=[WebEndpointObservation(url="http://127.0.0.1/", path="/", method="GET")]
            )]
        )
        self._run_zap_job(res)
        
        self.db.delete(self.assessment)
        self.db.commit()
        
        self.assertEqual(self.db.query(Asset).count(), 0)
        self.assertEqual(self.db.query(NetworkService).count(), 0)
        self.assertEqual(self.db.query(WebApplication).count(), 0)
        self.assertEqual(self.db.query(WebEndpoint).count(), 0)

if __name__ == "__main__":
    unittest.main()
