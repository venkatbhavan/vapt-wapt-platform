from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict
from collections import defaultdict

from app.core.database import get_db
from app.models.assessment import Assessment, Finding, ScanJob
from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.schemas.attack_surface import (
    AttackSurfaceRootResponse,
    AssetResponse,
    NetworkServiceResponse,
    WebApplicationResponse,
    WebEndpointResponse,
    AttackSurfaceFinding
)

router = APIRouter(
    prefix="/api",
    tags=["Attack Surface"]
)

@router.get("/assessments/{assessment_id}/attack-surface", response_model=AttackSurfaceRootResponse)
def get_assessment_attack_surface(assessment_id: int, db: Session = Depends(get_db)):
    # Verify assessment exists
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Fetch attack surface efficiently with eager loading
    assets = db.query(Asset).filter(Asset.assessment_id == assessment_id).options(
        joinedload(Asset.services),
        joinedload(Asset.web_applications).joinedload(WebApplication.endpoints)
    ).all()

    # Fetch findings associated with this assessment
    # A finding belongs to a scan job, which belongs to an assessment.
    findings = db.query(Finding).join(ScanJob).filter(ScanJob.assessment_id == assessment_id).all()

    # Group findings perfectly avoiding duplication.
    # Finding placement: map each finding to its MOST SPECIFIC identity.
    asset_findings = defaultdict(list)
    service_findings = defaultdict(list)
    webapp_findings = defaultdict(list)
    endpoint_findings = defaultdict(list)

    for f in findings:
        f_model = AttackSurfaceFinding.model_validate(f)
        if f.web_endpoint_id:
            endpoint_findings[f.web_endpoint_id].append(f_model)
        elif f.web_application_id:
            webapp_findings[f.web_application_id].append(f_model)
        elif f.network_service_id:
            service_findings[f.network_service_id].append(f_model)
        elif f.asset_id:
            asset_findings[f.asset_id].append(f_model)

    # Reconstruct the response hierarchy explicitly mapping findings
    response_assets = []
    
    for a in assets:
        a_model = AssetResponse.model_validate(a)
        a_model.findings = asset_findings.get(a.id, [])
        a_model.services = []
        a_model.web_applications = []
        
        for s in a.services:
            s_model = NetworkServiceResponse.model_validate(s)
            s_model.findings = service_findings.get(s.id, [])
            a_model.services.append(s_model)
            
        for wa in a.web_applications:
            wa_model = WebApplicationResponse.model_validate(wa)
            wa_model.findings = webapp_findings.get(wa.id, [])
            wa_model.endpoints = []
            
            for ep in wa.endpoints:
                ep_model = WebEndpointResponse.model_validate(ep)
                ep_model.findings = endpoint_findings.get(ep.id, [])
                wa_model.endpoints.append(ep_model)
                
            a_model.web_applications.append(wa_model)
            
        response_assets.append(a_model)
        
    return AttackSurfaceRootResponse(
        assessment_id=assessment_id,
        assets=response_assets
    )
