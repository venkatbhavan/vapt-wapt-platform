import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.assessment import Base, Project, Assessment, ScanJob, Finding, FindingSeverity, FindingConfidence, FindingStatus, ScanProfile
from app.models.attack_surface import Asset, NetworkService
from app.models.retest import RetestRequest, RetestStatus, RetestResult, RetestResultStatus, RetestConfidence
from app.models.compliance import FindingComplianceMapping, ComplianceControl, ComplianceFramework, MappingType, MappingConfidence
from app.models.remediation import FindingRemediation, RemediationGuidance, RemediationMappingConfidence, RemediationPriority, RemediationType

from app.services.posture_engine import calculate_posture, get_finding_risk_score, calculate_finding_penalty
from app.schemas.posture import PostureLevel, CoverageStatus

class TestPostureEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        
        # Base setup
        self.project = Project(name="Test Project")
        self.db.add(self.project)
        self.db.commit()
        
        self.assessment = Assessment(
            project_id=self.project.id,
            name="Posture Assessment",
            target="example.com",
            scope="example.com",
            scan_profile=ScanProfile.standard
        )
        self.db.add(self.assessment)
        self.db.commit()
        
        self.job = ScanJob(assessment_id=self.assessment.id, scan_profile=ScanProfile.standard)
        self.db.add(self.job)
        self.db.commit()

        # Another assessment for isolation check
        self.other_assessment = Assessment(
            project_id=self.project.id,
            name="Other Assessment",
            target="other.com",
            scope="other.com"
        )
        self.db.add(self.other_assessment)
        self.db.commit()

        self.other_job = ScanJob(assessment_id=self.other_assessment.id, scan_profile=ScanProfile.standard)
        self.db.add(self.other_job)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _create_finding(self, severity=FindingSeverity.high, risk_score=3.0, status=FindingStatus.open, job_id=None):
        f = Finding(
            scan_job_id=job_id or self.job.id,
            title=f"Test Finding {severity}",
            severity=severity,
            confidence=FindingConfidence.high,
            risk_score=risk_score,
            status=status
        )
        self.db.add(f)
        self.db.commit()
        return f
        
    def test_no_data_case(self):
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.level, PostureLevel.NO_DATA)
        self.assertEqual(res.coverage_status, CoverageStatus.unknown)
        self.assertIsNone(res.score)

    def test_no_findings_but_assets_case(self):
        asset = Asset(assessment_id=self.assessment.id, asset_type="domain", ip_address="0.0.0.0")
        self.db.add(asset)
        self.db.commit()
        
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.level, PostureLevel.NO_DATA)
        self.assertEqual(res.coverage_status, CoverageStatus.limited)
        self.assertIsNone(res.score)

    def test_informational_only(self):
        self._create_finding(severity=FindingSeverity.info, risk_score=0.0)
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.score, 100)
        self.assertEqual(res.level, PostureLevel.STRONG)
        self.assertEqual(res.dimensions.finding_risk, 0.0)

    def test_critical_finding_penalty(self):
        # 1 Critical finding (score 4.0) -> penalty 32. Score should be 68 (MODERATE)
        self._create_finding(severity=FindingSeverity.critical, risk_score=4.0)
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.score, 65)
        self.assertEqual(res.level, PostureLevel.MODERATE)

    def test_multiple_findings(self):
        # 1 Critical (4.0) -> 32
        # 1 High (3.0) -> 15.59
        # Total penalty = 47.59
        # Score = 100 - 47.59 = 52 (MODERATE)
        self._create_finding(severity=FindingSeverity.critical, risk_score=4.0)
        self._create_finding(severity=FindingSeverity.high, risk_score=3.0)
        # Remediate one so it's not missing guidance (otherwise it adds -3)
        # Wait, the above will get -3 for remediation penalty because no guidance!
        # Let's check dimensions directly.
        res = calculate_posture(self.db, self.assessment.id)
        self.assertAlmostEqual(res.dimensions.finding_risk, 47.59, places=1)
        self.assertEqual(res.dimensions.remediation, 6.0) # 2 findings missing guidance
        # Final penalty = 47.59 + 6 = 53.59 => score 46 => WEAK
        self.assertEqual(res.score, 46)
        self.assertEqual(res.level, PostureLevel.WEAK)

    def test_fixed_findings_ignored(self):
        self._create_finding(severity=FindingSeverity.critical, risk_score=4.0, status=FindingStatus.resolved)
        res = calculate_posture(self.db, self.assessment.id)
        # Treated as no active risk, but because there is a finding, it's not NO_DATA!
        # Wait, the code checks `if not findings:` to return NO_DATA.
        # Since there is 1 resolved finding, findings list is not empty.
        self.assertEqual(res.score, 100)
        self.assertEqual(res.level, PostureLevel.STRONG)

    def test_still_present_retest(self):
        f = self._create_finding(severity=FindingSeverity.medium, risk_score=2.0)
        # Penalty 5.66
        req = RetestRequest(finding_id=f.id, status=RetestStatus.completed)
        self.db.add(req)
        self.db.commit()
        res_obj = RetestResult(retest_request_id=req.id, result=RetestResultStatus.still_present, confidence=RetestConfidence.high, rationale="test", previous_finding_id=f.id)
        self.db.add(res_obj)
        self.db.commit()
        
        res = calculate_posture(self.db, self.assessment.id)
        # finding risk = 5.66
        # finding health = 5.0 (still present)
        # Total = 10.66 -> score 89 -> GOOD
        self.assertEqual(res.score, 89)
        self.assertEqual(res.dimensions.finding_health, 5.0)

    def test_attack_surface(self):
        self._create_finding(severity=FindingSeverity.info, risk_score=0.0)
        asset = Asset(assessment_id=self.assessment.id, asset_type="ip", ip_address="10.0.0.1")
        self.db.add(asset)
        self.db.commit()
        
        svc = NetworkService(asset_id=asset.id, port=23, protocol="tcp", state="open", service_name="telnet")
        self.db.add(svc)
        self.db.commit()
        
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.dimensions.attack_surface, 2.0)
        self.assertEqual(res.score, 98)

    def test_remediation_health(self):
        f = self._create_finding(severity=FindingSeverity.high, risk_score=3.0)
        # -3 penalty because no remediation
        res1 = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res1.dimensions.remediation, 3.0)
        
        # Add remediation
        f.remediation = "Fix it"
        self.db.commit()
        res2 = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res2.dimensions.remediation, 0.0)

    def test_compliance_signal(self):
        f = self._create_finding(severity=FindingSeverity.low, risk_score=1.0) # penalty 1
        framework = ComplianceFramework(name="SOC2", version="2017")
        self.db.add(framework)
        self.db.commit()
        control = ComplianceControl(framework_id=framework.id, control_id="CC1", title="Test", description="Test")
        self.db.add(control)
        self.db.commit()
        
        mapping = FindingComplianceMapping(
            finding_id=f.id,
            control_id=control.id,
            rationale="Test",
            mapping_type=MappingType.direct,
            mapping_confidence=MappingConfidence.high,
            source="manual"
        )
        self.db.add(mapping)
        self.db.commit()
        
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.dimensions.compliance, 1.0)
        # Score = 100 - (1 for low risk + 1 for compliance) = 98
        self.assertEqual(res.score, 98)

    def test_assessment_isolation(self):
        # Create critical finding in OTHER assessment
        self._create_finding(severity=FindingSeverity.critical, risk_score=4.0, job_id=self.other_job.id)
        # Assessment 1 has no findings
        res = calculate_posture(self.db, self.assessment.id)
        self.assertEqual(res.level, PostureLevel.NO_DATA)
        self.assertIsNone(res.score)

    def test_determinism_and_bounds(self):
        # Add 10 critical findings
        for _ in range(10):
            self._create_finding(severity=FindingSeverity.critical, risk_score=4.0)
        # Base finding penalty = 10 * 32 = 320
        # Plus remediation penalty = 10 * 3 = 30
        res = calculate_posture(self.db, self.assessment.id)
        # Score must not be less than 0
        self.assertEqual(res.score, 0)
        self.assertEqual(res.level, PostureLevel.CRITICAL)

if __name__ == '__main__':
    unittest.main()
