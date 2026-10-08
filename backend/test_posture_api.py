import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.assessment import Base, Assessment, Project, Finding, ScanJob, FindingSeverity

class TestPostureAPI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Setup base data
        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()
        
        self.assessment = Assessment(
            project_id=self.project.id,
            name="Posture Assessment",
            target="example.com",
            scope="example.com"
        )
        self.db.add(self.assessment)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        app.dependency_overrides.clear()

    def test_get_posture_success(self):
        response = self.client.get(f"/api/assessments/{self.assessment.id}/posture")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["level"], "no_data")
        self.assertIsNone(data["score"])

    def test_get_posture_not_found(self):
        response = self.client.get("/api/assessments/999/posture")
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
