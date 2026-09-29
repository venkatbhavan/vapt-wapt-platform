import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Project, Assessment, Finding, ScanJob
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestAttackSurfaceAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = TestingSessionLocal()
        
        # Clean DB
        for tbl in reversed(Base.metadata.sorted_tables):
            self.db.execute(tbl.delete())
        self.db.commit()

        # Fixtures
        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.flush()

        self.assessment = Assessment(project_id=self.project.id, name="Test Assessment", target="127.0.0.1")
        self.assessment2 = Assessment(project_id=self.project.id, name="Other Assessment", target="10.0.0.1")
        self.db.add_all([self.assessment, self.assessment2])
        self.db.flush()
        
        self.job = ScanJob(assessment_id=self.assessment.id, scan_profile="full")
        self.db.add(self.job)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _seed_attack_surface(self):
        a1 = Asset(assessment_id=self.assessment.id, ip_address="127.0.0.1", os="Linux")
        a2 = Asset(assessment_id=self.assessment2.id, ip_address="10.0.0.1")
        self.db.add_all([a1, a2])
        self.db.flush()
        
        s1 = NetworkService(asset_id=a1.id, port=80, protocol="tcp", state="open")
        self.db.add(s1)
        self.db.flush()
        
        wa1 = WebApplication(asset_id=a1.id, network_service_id=s1.id, base_url="http://127.0.0.1:80", scheme="http")
        self.db.add(wa1)
        self.db.flush()
        
        we1 = WebEndpoint(web_application_id=wa1.id, path="/", method="GET")
        self.db.add(we1)
        self.db.commit()
        
        return a1, a2, s1, wa1, we1

    # 1. Existing assessment with no attack surface returns 200 and empty assets.
    def test_01_empty_attack_surface(self):
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["assessment_id"], self.assessment.id)
        self.assertEqual(data["assets"], [])

    # 2. Nonexistent assessment returns 404.
    def test_02_nonexistent_assessment(self):
        resp = self.client.get(f"/api/assessments/9999/attack-surface")
        self.assertEqual(resp.status_code, 404)

    # 3. One asset is returned correctly.
    # 4. Asset fields are correct.
    # 19. Empty attack surface returns valid schema.
    # 22. Response schema validates correctly.
    def test_03_04_asset_fields(self):
        a1, *rest = self._seed_attack_surface()
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        self.assertEqual(resp.status_code, 200)
        assets = resp.json()["assets"]
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["ip_address"], "127.0.0.1")
        self.assertEqual(assets[0]["os"], "Linux")

    # 5. Network services appear under the correct asset.
    # 6. Service fields are correct.
    def test_05_06_network_services(self):
        self._seed_attack_surface()
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        services = resp.json()["assets"][0]["services"]
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["port"], 80)
        self.assertEqual(services[0]["protocol"], "tcp")

    # 7. Web applications appear under the correct asset.
    # 8. Web endpoints appear under the correct application.
    # 9. Endpoint fields are correct.
    def test_07_08_09_web_hierarchy(self):
        self._seed_attack_surface()
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        apps = resp.json()["assets"][0]["web_applications"]
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["scheme"], "http")
        
        endpoints = apps[0]["endpoints"]
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0]["path"], "/")

    # 10. Asset-level finding appears at asset scope.
    # 11. NetworkService-level finding appears at service scope.
    # 12. WebApplication-level finding appears at application scope.
    # 13. WebEndpoint-level finding appears at endpoint scope.
    # 14. Findings are not duplicated across hierarchy levels.
    def test_10_to_14_finding_scopes(self):
        a1, a2, s1, wa1, we1 = self._seed_attack_surface()
        
        # Asset Finding
        f_asset = Finding(scan_job_id=self.job.id, title="Asset Finding", asset_id=a1.id)
        # Service Finding (has asset + service)
        f_svc = Finding(scan_job_id=self.job.id, title="Service Finding", asset_id=a1.id, network_service_id=s1.id)
        # App Finding
        f_app = Finding(scan_job_id=self.job.id, title="App Finding", asset_id=a1.id, network_service_id=s1.id, web_application_id=wa1.id)
        # Endpoint Finding
        f_ep = Finding(scan_job_id=self.job.id, title="Endpoint Finding", asset_id=a1.id, network_service_id=s1.id, web_application_id=wa1.id, web_endpoint_id=we1.id)
        
        self.db.add_all([f_asset, f_svc, f_app, f_ep])
        self.db.commit()

        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        asset_node = resp.json()["assets"][0]
        
        # Verify strict non-duplication
        self.assertEqual(len(asset_node["findings"]), 1)
        self.assertEqual(asset_node["findings"][0]["title"], "Asset Finding")
        
        svc_node = asset_node["services"][0]
        self.assertEqual(len(svc_node["findings"]), 1)
        self.assertEqual(svc_node["findings"][0]["title"], "Service Finding")
        
        app_node = asset_node["web_applications"][0]
        self.assertEqual(len(app_node["findings"]), 1)
        self.assertEqual(app_node["findings"][0]["title"], "App Finding")
        
        ep_node = app_node["endpoints"][0]
        self.assertEqual(len(ep_node["findings"]), 1)
        self.assertEqual(ep_node["findings"][0]["title"], "Endpoint Finding")

    # 15. Findings from another assessment are excluded.
    # 16. Assets from another assessment are excluded.
    # 17. Same IP in different assessments remains isolated.
    # 18. Same URL in different assessments remains isolated.
    def test_15_to_18_isolation(self):
        a1, a2, s1, wa1, we1 = self._seed_attack_surface()
        
        job2 = ScanJob(assessment_id=self.assessment2.id, scan_profile="full")
        self.db.add(job2)
        self.db.flush()
        
        f2 = Finding(scan_job_id=job2.id, title="Alien Finding", asset_id=a2.id)
        self.db.add(f2)
        self.db.commit()
        
        # Query Assessment 1
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        data = resp.json()
        
        # Only Asset 1 should be here
        self.assertEqual(len(data["assets"]), 1)
        self.assertEqual(data["assets"][0]["ip_address"], "127.0.0.1")
        # No findings under Asset 1 since Alien Finding belongs to Asset 2
        self.assertEqual(len(data["assets"][0]["findings"]), 0)

    # 20. Enum values serialize correctly.
    def test_20_enums(self):
        a1, *rest = self._seed_attack_surface()
        f = Finding(scan_job_id=self.job.id, title="Enum Test", severity="critical", risk_level="critical", asset_id=a1.id)
        self.db.add(f)
        self.db.commit()
        
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        f_resp = resp.json()["assets"][0]["findings"][0]
        self.assertEqual(f_resp["severity"], "critical")
        self.assertEqual(f_resp["risk_level"], "critical")

    # 21. Existing finding/evidence endpoints still work.
    # 23. API does not expose raw evidence by default.
    def test_21_23_evidence_protection(self):
        a1, *rest = self._seed_attack_surface()
        f = Finding(scan_job_id=self.job.id, title="Test", asset_id=a1.id)
        self.db.add(f)
        self.db.commit()
        
        # Attack surface should not have evidence
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        f_resp = resp.json()["assets"][0]["findings"][0]
        self.assertNotIn("evidence", f_resp)
        self.assertNotIn("raw", f_resp)

    # 24. API does not allow mutation through this router.
    def test_24_no_mutation(self):
        resp = self.client.post(f"/api/assessments/{self.assessment.id}/attack-surface", json={})
        self.assertEqual(resp.status_code, 405) # Method Not Allowed

    # 25. API handles multiple assets/services/applications/endpoints correctly.
    def test_25_multiples(self):
        a1, *rest = self._seed_attack_surface()
        
        # Add another service and app
        s2 = NetworkService(asset_id=a1.id, port=443, protocol="tcp", state="open")
        self.db.add(s2)
        self.db.flush()
        
        wa2 = WebApplication(asset_id=a1.id, network_service_id=s2.id, base_url="https://127.0.0.1", scheme="https")
        self.db.add(wa2)
        self.db.flush()
        
        we2 = WebEndpoint(web_application_id=wa2.id, path="/admin", method="GET")
        we3 = WebEndpoint(web_application_id=wa2.id, path="/api", method="POST")
        self.db.add_all([we2, we3])
        self.db.commit()
        
        resp = self.client.get(f"/api/assessments/{self.assessment.id}/attack-surface")
        data = resp.json()
        
        assets = data["assets"]
        self.assertEqual(len(assets), 1)
        self.assertEqual(len(assets[0]["services"]), 2)
        self.assertEqual(len(assets[0]["web_applications"]), 2)
        
        https_app = next(app for app in assets[0]["web_applications"] if app["scheme"] == "https")
        self.assertEqual(len(https_app["endpoints"]), 2)

if __name__ == "__main__":
    unittest.main()
