import sys
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.assessment import Base, Project, Assessment, ScanJob, ScanProfile, AssessmentStatus, ScanJobStatus
from app.core import database

# In-memory DB for isolated testing (using shared cache to allow multiple sessions)
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Monkeypatch the database session for the background worker test BEFORE importing the service
database.SessionLocal = SessionLocal

from app.worker.service import process_scan_job, run_scan_job_background


def test_worker():
    db = SessionLocal()
    try:
        # Seed test data
        project = Project(name="Test Project")
        db.add(project)
        db.commit()
        db.refresh(project)

        # 1. Authorized Assessment
        assessment_auth = Assessment(
            project_id=project.id,
            name="Auth Assessment",
            target="http://example.com",
            scope="Everything",
            authorization_confirmed=True
        )
        db.add(assessment_auth)
        
        # 2. Unauthorized Assessment
        assessment_no_auth = Assessment(
            project_id=project.id,
            name="No Auth Assessment",
            target="http://example.com",
            scope="Everything",
            authorization_confirmed=False
        )
        db.add(assessment_no_auth)
        db.commit()

        # Jobs
        job_valid = ScanJob(assessment_id=assessment_auth.id, scan_profile=ScanProfile.passive)
        job_unauth = ScanJob(assessment_id=assessment_no_auth.id, scan_profile=ScanProfile.passive)
        db.add_all([job_valid, job_unauth])
        db.commit()

        # Test 1: unauthorized assessment cannot run
        try:
            process_scan_job(db, job_unauth.id)
            assert False, "Should have raised ValueError for missing authorization"
        except ValueError as e:
            assert "Authorization not confirmed" in str(e)
            # Job status should be failed
            db.refresh(job_unauth)
            assert job_unauth.status == ScanJobStatus.failed

        # Test 2: queued job successfully becomes completed & result_json is stored using background execution
        db.commit() # ensure everything is fully committed before new session
        
        print(f"Status before background execution: {job_valid.status}")
        
        # Using background wrapper which opens its own session
        run_scan_job_background(job_valid.id)
        
        # Must expire/refresh the object to load changes made by another session
        db.expire_all()
        db.refresh(job_valid)
        print(f"Status after background execution: {job_valid.status}")
        
        assert job_valid.status == ScanJobStatus.completed
        assert job_valid.result_json is not None
        result_data = json.loads(job_valid.result_json)
        assert result_data["scanner"] == "mock"
        assert result_data["target"] == "http://example.com"
        assert len(result_data["findings"]) > 0

        # Test 3: non-queued job cannot run
        try:
            process_scan_job(db, job_valid.id)
            assert False, "Should have raised ValueError for non-queued state"
        except ValueError as e:
            assert "Cannot run job in state" in str(e)

        print("All worker local tests passed successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    test_worker()
