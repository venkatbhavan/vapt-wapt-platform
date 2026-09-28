import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.core.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.assessment import Base, Project, Assessment, ScanProfile
from app.api.scan_jobs import create_scan_job
from app.schemas.scanjob import ScanJobCreate

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestActiveScanAuth(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        p = Project(name="Test Project")
        self.db.add(p)
        self.db.flush()
        
        self.project_id = p.id
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def create_assessment(self, profile):
        a = Assessment(
            project_id=self.project_id,
            name="A1",
            target="127.0.0.1",
            scope="test",
            authorization_confirmed=True,
            scan_profile=profile
        )
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a.id

    def test_passive_scan_accepted_without_confirmation(self):
        a_id = self.create_assessment("passive")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=False)
        job = create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        self.assertIsNotNone(job)

    def test_safe_scan_accepted_without_confirmation(self):
        a_id = self.create_assessment("safe")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=False)
        job = create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        self.assertIsNotNone(job)

    def test_standard_scan_accepted_without_confirmation(self):
        a_id = self.create_assessment("standard")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=False)
        job = create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        self.assertIsNotNone(job)

    def test_active_scan_rejected_without_confirmation(self):
        a_id = self.create_assessment("active")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=False)
        
        with self.assertRaises(HTTPException) as ctx:
            create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Explicit confirmation", ctx.exception.detail)

    def test_active_scan_accepted_with_confirmation(self):
        a_id = self.create_assessment("active")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=True)
        job = create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        self.assertIsNotNone(job)

    def test_deep_scan_rejected_without_confirmation(self):
        a_id = self.create_assessment("deep")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=False)
        
        with self.assertRaises(HTTPException) as ctx:
            create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        
        self.assertEqual(ctx.exception.status_code, 400)

    def test_deep_scan_accepted_with_confirmation(self):
        a_id = self.create_assessment("deep")
        bg_tasks = MagicMock()
        payload = ScanJobCreate(active_scan_confirmed=True)
        job = create_scan_job(assessment_id=a_id, payload=payload, background_tasks=bg_tasks, db=self.db)
        self.assertIsNotNone(job)

if __name__ == "__main__":
    unittest.main()
