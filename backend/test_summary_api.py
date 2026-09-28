from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.api.assessments import get_assessment_summary
from app.models.assessment import Base, Project, Assessment, ScanJob, ScanProfile, Finding, FindingSeverity, FindingStatus, ScanJobStatus
from app.risk.models import RiskLevel

# Setup test db
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def setup_data():
    db = TestingSessionLocal()
    
    # 1. Empty assessment
    p1 = Project(name="Project 1")
    db.add(p1)
    db.commit()
    a1 = Assessment(project_id=p1.id, name="Empty Assessment", target="http://empty.com", scope="all")
    db.add(a1)
    db.commit()
    
    # 2. Populated assessment
    a2 = Assessment(project_id=p1.id, name="Populated Assessment", target="http://pop.com", scope="all")
    db.add(a2)
    db.commit()
    
    # Scan jobs for a2
    sj1 = ScanJob(assessment_id=a2.id, scan_profile=ScanProfile.passive, status=ScanJobStatus.completed)
    sj2 = ScanJob(assessment_id=a2.id, scan_profile=ScanProfile.safe, status=ScanJobStatus.running)
    db.add(sj1)
    db.add(sj2)
    db.commit()
    
    # Findings for sj1
    f1 = Finding(scan_job_id=sj1.id, title="F1", severity=FindingSeverity.high, risk_level=RiskLevel.critical, status=FindingStatus.open)
    f2 = Finding(scan_job_id=sj1.id, title="F2", severity=FindingSeverity.low, risk_level=RiskLevel.low, status=FindingStatus.resolved)
    
    # Findings for sj2
    f3 = Finding(scan_job_id=sj2.id, title="F3", severity=FindingSeverity.high, risk_level=RiskLevel.high, status=FindingStatus.open)
    
    db.add_all([f1, f2, f3])
    db.commit()
    
    # 3. Another assessment to ensure separation
    a3 = Assessment(project_id=p1.id, name="Other Assessment", target="http://other.com", scope="all")
    db.add(a3)
    db.commit()
    sj3 = ScanJob(assessment_id=a3.id, scan_profile=ScanProfile.passive, status=ScanJobStatus.completed)
    db.add(sj3)
    db.commit()
    f4 = Finding(scan_job_id=sj3.id, title="F4", severity=FindingSeverity.critical, risk_level=RiskLevel.critical, status=FindingStatus.open)
    db.add(f4)
    db.commit()
    
    return a1.id, a2.id, a3.id

def test_summary_api():
    a1_id, a2_id, a3_id = setup_data()
    db = TestingSessionLocal()
    
    # Case 1: Assessment with no scan jobs
    data1 = get_assessment_summary(a1_id, db)
    assert data1.total_findings == 0
    assert data1.scan_job_counts.completed == 0
    
    # Case 2-6: Populated assessment
    data2 = get_assessment_summary(a2_id, db)
    
    assert data2.total_findings == 3
    
    assert data2.severity_counts.high == 2
    assert data2.severity_counts.low == 1
    assert data2.severity_counts.critical == 0
    
    assert data2.risk_counts.critical == 1
    assert data2.risk_counts.high == 1
    assert data2.risk_counts.low == 1
    
    assert data2.status_counts.open == 2
    assert data2.status_counts.resolved == 1
    
    assert data2.scan_job_counts.completed == 1
    assert data2.scan_job_counts.running == 1
    assert data2.scan_job_counts.queued == 0
    
    # Case 7: Nonexistent assessment
    try:
        get_assessment_summary(999, db)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 404

    print("Summary API tests passed successfully!")

if __name__ == "__main__":
    test_summary_api()
