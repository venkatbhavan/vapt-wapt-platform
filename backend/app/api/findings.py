from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.assessment import Finding as FindingModel, Evidence as EvidenceModel, ScanJob as ScanJobModel
from app.schemas.finding import Finding, Evidence

router = APIRouter(tags=["findings"])

@router.get("/api/scan-jobs/{scan_job_id}/findings", response_model=List[Finding])
def get_scan_job_findings(scan_job_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_scan_job = db.query(ScanJobModel).filter(ScanJobModel.id == scan_job_id).first()
    if not db_scan_job:
        raise HTTPException(status_code=404, detail="Scan job not found")
        
    findings = db.query(FindingModel).filter(FindingModel.scan_job_id == scan_job_id).offset(skip).limit(limit).all()
    return findings

@router.get("/api/findings/{finding_id}", response_model=Finding)
def get_finding(finding_id: int, db: Session = Depends(get_db)):
    finding = db.query(FindingModel).filter(FindingModel.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding

@router.get("/api/findings/{finding_id}/evidence", response_model=List[Evidence])
def get_finding_evidence(finding_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    finding = db.query(FindingModel).filter(FindingModel.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    evidence_list = db.query(EvidenceModel).filter(EvidenceModel.finding_id == finding_id).offset(skip).limit(limit).all()
    return evidence_list
