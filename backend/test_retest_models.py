import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError
from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity
from app.models.retest import RetestRequest, RetestResult, RetestStatus, RetestResultStatus, RetestConfidence

class TestRetestModels(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite for testing
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()

        # Seed basic assessment hierarchy required for finding
        self.project = Project(name="Test Project", description="Test")
        self.db.add(self.project)
        self.db.commit()

        self.assessment = Assessment(
            project_id=self.project.id,
            name="Test Assessment",
            target="example.com",
            scan_profile="standard",
            status="running",
            authorization_confirmed=True,
            scope="external"
        )
        self.db.add(self.assessment)
        self.db.commit()

        self.scan_job = ScanJob(
            assessment_id=self.assessment.id,
            scan_profile="standard",
            active_scan_confirmed=True,
            status="completed"
        )
        self.db.add(self.scan_job)
        self.db.commit()

        self.finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Test Finding",
            severity=FindingSeverity.medium
        )
        self.db.add(self.finding)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_retest_request_creation(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        self.assertIsNotNone(req.id)
        self.assertEqual(req.finding_id, self.finding.id)
        self.assertEqual(req.status, RetestStatus.requested)
        self.assertIsNotNone(req.requested_at)
        self.assertIsNotNone(req.created_at)
        self.assertIsNotNone(req.updated_at)
        self.assertIsNone(req.started_at)
        self.assertIsNone(req.completed_at)

    def test_retest_request_finding_relationship(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        # Check Finding.retest_requests
        self.assertEqual(len(self.finding.retest_requests), 1)
        self.assertEqual(self.finding.retest_requests[0].id, req.id)
        
        # Check RetestRequest.finding
        self.assertEqual(req.finding.id, self.finding.id)

    def test_retest_status_enum(self):
        self.assertEqual(RetestStatus.requested.value, "requested")
        self.assertEqual(RetestStatus.running.value, "running")
        self.assertEqual(RetestStatus.completed.value, "completed")
        self.assertEqual(RetestStatus.failed.value, "failed")

    def test_retest_result_creation_and_relationships(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        result = RetestResult(
            retest_request_id=req.id,
            previous_finding_id=self.finding.id,
            result=RetestResultStatus.fixed,
            confidence=RetestConfidence.high,
            rationale="Verified fixed."
        )
        self.db.add(result)
        self.db.commit()

        self.assertIsNotNone(result.id)
        self.assertEqual(result.retest_request_id, req.id)
        self.assertEqual(result.previous_finding_id, self.finding.id)
        self.assertIsNone(result.current_finding_id)
        self.assertEqual(result.result, RetestResultStatus.fixed)
        
        # Test relationships
        self.assertEqual(result.retest_request.id, req.id)
        self.assertEqual(result.previous_finding.id, self.finding.id)
        self.assertIsNone(result.current_finding)

    def test_retest_result_with_current_finding(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        # Create a new finding to represent current state
        new_finding = Finding(
            scan_job_id=self.scan_job.id,
            title="Test Finding (Changed)",
            severity=FindingSeverity.low
        )
        self.db.add(new_finding)
        self.db.commit()

        result = RetestResult(
            retest_request_id=req.id,
            previous_finding_id=self.finding.id,
            current_finding_id=new_finding.id,
            result=RetestResultStatus.changed,
            confidence=RetestConfidence.medium,
            rationale="Still present but severity changed."
        )
        self.db.add(result)
        self.db.commit()

        self.assertEqual(result.current_finding.id, new_finding.id)
        self.assertEqual(result.current_finding_id, new_finding.id)

    def test_retest_result_status_enum(self):
        self.assertEqual(RetestResultStatus.fixed.value, "fixed")
        self.assertEqual(RetestResultStatus.still_present.value, "still_present")
        self.assertEqual(RetestResultStatus.changed.value, "changed")
        self.assertEqual(RetestResultStatus.inconclusive.value, "inconclusive")

    def test_retest_confidence_enum(self):
        self.assertEqual(RetestConfidence.low.value, "low")
        self.assertEqual(RetestConfidence.medium.value, "medium")
        self.assertEqual(RetestConfidence.high.value, "high")

    def test_multiple_retests_for_same_finding(self):
        req1 = RetestRequest(finding_id=self.finding.id)
        req2 = RetestRequest(finding_id=self.finding.id)
        self.db.add_all([req1, req2])
        self.db.commit()

        res1 = RetestResult(
            retest_request_id=req1.id,
            previous_finding_id=self.finding.id,
            result=RetestResultStatus.still_present,
            confidence=RetestConfidence.high,
            rationale="Failed."
        )
        res2 = RetestResult(
            retest_request_id=req2.id,
            previous_finding_id=self.finding.id,
            result=RetestResultStatus.fixed,
            confidence=RetestConfidence.high,
            rationale="Fixed."
        )
        self.db.add_all([res1, res2])
        self.db.commit()

        self.assertEqual(len(self.finding.retest_requests), 2)
        self.assertEqual(self.finding.retest_requests[0].result.result, RetestResultStatus.still_present)
        self.assertEqual(self.finding.retest_requests[1].result.result, RetestResultStatus.fixed)

    def test_finding_deletion_cascade(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()
        
        req_id = req.id

        result = RetestResult(
            retest_request_id=req.id,
            previous_finding_id=self.finding.id,
            result=RetestResultStatus.fixed,
            confidence=RetestConfidence.high,
            rationale="Fixed"
        )
        self.db.add(result)
        self.db.commit()
        
        res_id = result.id

        self.db.delete(self.finding)
        self.db.commit()

        # RetestRequest should be deleted
        self.assertIsNone(self.db.query(RetestRequest).filter_by(id=req_id).first())
        # RetestResult should be deleted
        self.assertIsNone(self.db.query(RetestResult).filter_by(id=res_id).first())

    def test_retest_request_deletion_cascade(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        result = RetestResult(
            retest_request_id=req.id,
            previous_finding_id=self.finding.id,
            result=RetestResultStatus.fixed,
            confidence=RetestConfidence.high,
            rationale="Fixed"
        )
        self.db.add(result)
        self.db.commit()
        
        res_id = result.id

        self.db.delete(req)
        self.db.commit()

        # RetestResult should be deleted
        self.assertIsNone(self.db.query(RetestResult).filter_by(id=res_id).first())
        
        # Finding should NOT be deleted
        self.assertIsNotNone(self.db.query(Finding).filter_by(id=self.finding.id).first())

    def test_current_finding_no_accidental_delete(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        new_finding = Finding(
            scan_job_id=self.scan_job.id,
            title="New Finding",
            severity=FindingSeverity.medium
        )
        self.db.add(new_finding)
        self.db.commit()

        result = RetestResult(
            retest_request_id=req.id,
            previous_finding_id=self.finding.id,
            current_finding_id=new_finding.id,
            result=RetestResultStatus.changed,
            confidence=RetestConfidence.high,
            rationale="Changed"
        )
        self.db.add(result)
        self.db.commit()

        self.db.delete(result)
        self.db.commit()

        # Deleting the result should not delete either finding
        self.assertIsNotNone(self.db.query(Finding).filter_by(id=self.finding.id).first())
        self.assertIsNotNone(self.db.query(Finding).filter_by(id=new_finding.id).first())

    def test_assessment_isolation_derived(self):
        # Assessment isolation is derived through Finding -> ScanJob -> Assessment
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        self.assertEqual(req.finding.scan_job.assessment.id, self.assessment.id)

    def test_required_fields_retest_request(self):
        # finding_id is required
        req = RetestRequest()
        self.db.add(req)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_required_fields_retest_result(self):
        req = RetestRequest(finding_id=self.finding.id)
        self.db.add(req)
        self.db.commit()

        # missing previous_finding_id, result, confidence, rationale
        res = RetestResult(retest_request_id=req.id)
        self.db.add(res)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

if __name__ == '__main__':
    unittest.main()
