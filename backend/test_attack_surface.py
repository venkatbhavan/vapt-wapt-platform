import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models.assessment import Base, Project, Assessment, Finding, FindingSeverity
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint

class TestAttackSurfaceModels(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()

        self.assessment = Assessment(project_id=self.project.id, name="Test Assessment", target="192.168.1.0/24", scope="192.168.1.0/24")
        self.db.add(self.assessment)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_asset_creation_and_relationship(self):
        # 1. Asset belongs to an assessment
        # 2. Multiple assets can belong to one assessment
        asset1 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10", hostname="host1.local")
        asset2 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.11", hostname="host2.local")
        
        self.db.add_all([asset1, asset2])
        self.db.commit()

        self.assertEqual(len(self.assessment.assets), 2)
        self.assertEqual(self.assessment.assets[0].ip_address, "192.168.1.10")

    def test_service_creation_and_relationship(self):
        # 3. Services belong to an asset
        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset)
        self.db.commit()

        service1 = NetworkService(asset_id=asset.id, port=80, protocol="tcp", state="open", service_name="http")
        service2 = NetworkService(asset_id=asset.id, port=443, protocol="tcp", state="open", service_name="https")
        self.db.add_all([service1, service2])
        self.db.commit()

        self.assertEqual(len(asset.services), 2)
        self.assertEqual(asset.services[0].port, 80)

    def test_web_application_and_endpoint(self):
        # 4. Web applications belong to the appropriate asset/service relationship.
        # 5. Endpoints belong to a web application.
        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset)
        self.db.commit()

        service = NetworkService(asset_id=asset.id, port=443, protocol="tcp", state="open")
        self.db.add(service)
        self.db.commit()

        webapp = WebApplication(
            asset_id=asset.id,
            network_service_id=service.id,
            base_url="https://192.168.1.10",
            scheme="https"
        )
        self.db.add(webapp)
        self.db.commit()

        endpoint = WebEndpoint(
            web_application_id=webapp.id,
            path="/api/v1/users",
            method="GET"
        )
        self.db.add(endpoint)
        self.db.commit()

        self.assertEqual(len(asset.web_applications), 1)
        self.assertEqual(len(service.web_applications), 1)
        self.assertEqual(len(webapp.endpoints), 1)
        self.assertEqual(webapp.endpoints[0].path, "/api/v1/users")

    def test_idempotency_asset_and_service(self):
        # 6. Duplicate asset/service records are prevented safely
        asset1 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset1)
        self.db.commit()

        # Duplicate Asset
        asset2 = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        # Unique service
        service1 = NetworkService(asset_id=asset1.id, port=80, protocol="tcp", state="open")
        self.db.add(service1)
        self.db.commit()

        # Duplicate Service
        service2 = NetworkService(asset_id=asset1.id, port=80, protocol="tcp", state="closed")
        self.db.add(service2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_idempotency_webapp_and_endpoint(self):
        # 7. Duplicate web applications/endpoints are handled consistently
        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset)
        self.db.commit()

        webapp1 = WebApplication(asset_id=asset.id, base_url="http://192.168.1.10", scheme="http")
        self.db.add(webapp1)
        self.db.commit()

        webapp2 = WebApplication(asset_id=asset.id, base_url="http://192.168.1.10", scheme="http")
        self.db.add(webapp2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        endpoint1 = WebEndpoint(web_application_id=webapp1.id, path="/", method="GET")
        self.db.add(endpoint1)
        self.db.commit()

        endpoint2 = WebEndpoint(web_application_id=webapp1.id, path="/", method="GET")
        self.db.add(endpoint2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_cascade_deletion(self):
        # 8. Deleting an assessment does not leave orphaned attack-surface records
        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset)
        self.db.commit()

        service = NetworkService(asset_id=asset.id, port=80, protocol="tcp", state="open")
        self.db.add(service)
        
        webapp = WebApplication(asset_id=asset.id, network_service_id=service.id, base_url="http://192.168.1.10", scheme="http")
        self.db.add(webapp)
        
        self.db.commit()

        endpoint = WebEndpoint(web_application_id=webapp.id, path="/", method="GET")
        self.db.add(endpoint)
        self.db.commit()

        # Delete assessment
        self.db.delete(self.assessment)
        self.db.commit()

        self.assertEqual(self.db.query(Asset).count(), 0)
        self.assertEqual(self.db.query(NetworkService).count(), 0)
        self.assertEqual(self.db.query(WebApplication).count(), 0)
        self.assertEqual(self.db.query(WebEndpoint).count(), 0)

    def test_finding_correlation(self):
        # 9. Existing Finding relationships continue to work, and can link to attack surface
        from app.models.assessment import ScanJob
        job = ScanJob(assessment_id=self.assessment.id, scan_profile="passive")
        self.db.add(job)
        self.db.commit()

        asset = Asset(assessment_id=self.assessment.id, ip_address="192.168.1.10")
        self.db.add(asset)
        self.db.commit()

        finding = Finding(
            scan_job_id=job.id,
            title="Test Finding",
            severity=FindingSeverity.high,
            asset_id=asset.id
        )
        self.db.add(finding)
        self.db.commit()

        # Fetch finding and verify relationships
        f = self.db.query(Finding).first()
        self.assertIsNotNone(f.asset)
        self.assertEqual(f.asset.ip_address, "192.168.1.10")
        
        # Ensure it works in reverse
        self.assertEqual(len(asset.findings), 1)
        self.assertEqual(asset.findings[0].title, "Test Finding")

if __name__ == "__main__":
    unittest.main()
