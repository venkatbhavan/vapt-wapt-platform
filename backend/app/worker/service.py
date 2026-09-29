from datetime import datetime
from sqlalchemy.orm import Session
from app.models.assessment import ScanJob, Assessment, ScanJobStatus
from .scanners import get_scanner
from app.core.database import SessionLocal

def process_scan_job(db: Session, scan_job_id: int) -> ScanJob:
    # 1. Load ScanJob
    scan_job = db.query(ScanJob).filter(ScanJob.id == scan_job_id).first()
    if not scan_job:
        raise ValueError("ScanJob not found")

    # 2. Verify status is queued
    if scan_job.status != ScanJobStatus.queued:
        raise ValueError(f"Cannot run job in state: {scan_job.status}")

    # 3. Load Parent Assessment
    assessment = db.query(Assessment).filter(Assessment.id == scan_job.assessment_id).first()
    if not assessment:
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = "Parent Assessment not found"
        scan_job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(scan_job)
        raise ValueError("Parent Assessment not found")

    # 4. Independent Authorization Check
    if not assessment.authorization_confirmed:
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = "Authorization not confirmed on parent Assessment"
        scan_job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(scan_job)
        raise ValueError("Authorization not confirmed")

    # 5. Transition to Running
    scan_job.status = ScanJobStatus.running
    scan_job.started_at = datetime.utcnow()
    db.commit()

    # 6. Execute Scanner Adapter
    try:
        scanner = get_scanner(scan_job.scan_profile)
        result = scanner.scan(target=assessment.target, scan_profile=scan_job.scan_profile)

        # Persist Findings and Evidence
        from app.models.assessment import Finding as FindingModel, FindingSeverity, Evidence as EvidenceModel, EvidenceType
        from app.risk.engine import calculate_risk

        for f_data in result.findings:
            severity_mapped = f_data.severity if hasattr(FindingSeverity, f_data.severity) else "info"

            # Extract confidence if available; mock scanner doesn't produce it currently, but handle safely
            confidence = getattr(f_data, 'confidence', None)
            risk_result = calculate_risk(severity_mapped, confidence)

            db_finding = FindingModel(
                scan_job_id=scan_job.id,
                title=f_data.title,
                description=f_data.description,
                severity=severity_mapped,
                confidence=confidence,
                category=getattr(f_data, 'category', None),
                location=getattr(f_data, 'location', None),
                impact=getattr(f_data, 'impact', None),
                remediation=getattr(f_data, 'remediation', None),
                risk_score=risk_result.score,
                risk_level=risk_result.level,
                risk_rationale=risk_result.rationale
            )
            db.add(db_finding)
            db.flush() # flush to get the finding id

            for e_data in f_data.evidence:
                evidence_type_mapped = e_data.evidence_type if hasattr(EvidenceType, e_data.evidence_type) else "text"
                db_evidence = EvidenceModel(
                    finding_id=db_finding.id,
                    evidence_type=evidence_type_mapped,
                    title=e_data.title,
                    content=e_data.content,
                    source=e_data.source
                )
                db.add(db_evidence)

        # Ingestion of Attack Surface Data (Phase 6B)
        from app.models.attack_surface import Asset, NetworkService

        if hasattr(result, 'hosts') and result.hosts:
            for h_data in result.hosts:
                # 1. Find or create Asset idempotenly
                asset = db.query(Asset).filter(
                    Asset.assessment_id == assessment.id,
                    Asset.ip_address == h_data.ip_address
                ).first()

                if not asset:
                    asset = Asset(
                        assessment_id=assessment.id,
                        ip_address=h_data.ip_address,
                        hostname=h_data.hostname,
                        os=h_data.os
                    )
                    db.add(asset)
                    db.flush()
                else:
                    # Update mutable fields
                    if h_data.hostname and not asset.hostname:
                        asset.hostname = h_data.hostname
                    if h_data.os and not asset.os:
                        asset.os = h_data.os

                # 2. Find or create Services idempotenly
                for s_data in h_data.services:
                    svc = db.query(NetworkService).filter(
                        NetworkService.asset_id == asset.id,
                        NetworkService.port == s_data.port,
                        NetworkService.protocol == s_data.protocol
                    ).first()

                    if not svc:
                        svc = NetworkService(
                            asset_id=asset.id,
                            port=s_data.port,
                            protocol=s_data.protocol,
                            state=s_data.state,
                            service_name=s_data.service_name,
                            service_product=s_data.service_product,
                            service_version=s_data.service_version,
                            extra_info=s_data.extra_info
                        )
                        db.add(svc)
                    else:
                        # Update mutable fields with better information
                        if s_data.state:
                            svc.state = s_data.state
                        if s_data.service_name and s_data.service_name != 'unknown':
                            svc.service_name = s_data.service_name
                        if s_data.service_product:
                            svc.service_product = s_data.service_product
                        if s_data.service_version:
                            svc.service_version = s_data.service_version
                        if s_data.extra_info:
                            svc.extra_info = s_data.extra_info

        # Ingestion of Web Attack Surface Data (Phase 6C)
        if hasattr(result, 'web_applications') and result.web_applications:
            import socket
            import ipaddress
            import logging

            def is_ip_address(addr: str) -> bool:
                try:
                    ipaddress.ip_address(addr)
                    return True
                except ValueError:
                    return False

            from app.models.attack_surface import WebApplication, WebEndpoint
            for w_data in result.web_applications:
                # 1. Identity Resolution Strategy
                is_ip = is_ip_address(w_data.hostname)
                asset = None

                if is_ip:
                    asset = db.query(Asset).filter(
                        Asset.assessment_id == assessment.id,
                        Asset.ip_address == w_data.hostname
                    ).first()
                else:
                    # Hostname-first strategy
                    asset = db.query(Asset).filter(
                        Asset.assessment_id == assessment.id,
                        Asset.hostname == w_data.hostname
                    ).first()

                    if not asset:
                        # Attempt safe resolution to find an existing IP
                        try:
                            resolved_ip = socket.gethostbyname(w_data.hostname)
                            asset = db.query(Asset).filter(
                                Asset.assessment_id == assessment.id,
                                Asset.ip_address == resolved_ip
                            ).first()
                        except Exception:
                            pass

                # 2. Asset Creation with Semantic Safety
                if not asset:
                    if is_ip:
                        ip_to_use = w_data.hostname
                        host_to_use = None
                    else:
                        try:
                            ip_to_use = socket.gethostbyname(w_data.hostname)
                        except Exception:
                            ip_to_use = None
                        host_to_use = w_data.hostname

                    if not ip_to_use:
                        logging.getLogger(__name__).warning(
                            f"Schema limitation: Cannot ingest attack surface for {w_data.hostname} because it cannot be resolved to an IP address."
                        )
                        continue # Skip to next web_application

                    asset = Asset(
                        assessment_id=assessment.id,
                        ip_address=ip_to_use,
                        hostname=host_to_use
                    )
                    db.add(asset)
                    db.flush()


                # 2. Find or create NetworkService
                svc = db.query(NetworkService).filter(
                    NetworkService.asset_id == asset.id,
                    NetworkService.port == w_data.port,
                    NetworkService.protocol == "tcp"
                ).first()

                if not svc:
                    svc = NetworkService(
                        asset_id=asset.id,
                        port=w_data.port,
                        protocol="tcp",
                        state="open",
                        service_name=w_data.scheme
                    )
                    db.add(svc)
                    db.flush()

                # 3. Find or Create Web Application
                app = db.query(WebApplication).filter(
                    WebApplication.asset_id == asset.id,
                    WebApplication.base_url == w_data.base_url
                ).first()

                if not app:
                    app = WebApplication(
                        asset_id=asset.id,
                        network_service_id=svc.id,
                        base_url=w_data.base_url,
                        hostname=w_data.hostname,
                        port=w_data.port,
                        scheme=w_data.scheme,
                        title=w_data.title,
                        tech_info=w_data.tech_info
                    )
                    db.add(app)
                    db.flush()
                else:
                    if w_data.title:
                        app.title = w_data.title
                    if w_data.tech_info:
                        app.tech_info = w_data.tech_info

                # 4. Find or Create Endpoints
                for ep_data in w_data.endpoints:
                    ep = db.query(WebEndpoint).filter(
                        WebEndpoint.web_application_id == app.id,
                        WebEndpoint.path == ep_data.path,
                        WebEndpoint.method == ep_data.method
                    ).first()

                    if not ep:
                        ep = WebEndpoint(
                            web_application_id=app.id,
                            path=ep_data.path,
                            method=ep_data.method,
                            status_code=ep_data.status_code,
                            content_type=ep_data.content_type,
                            source=ep_data.discovered_from
                        )
                        db.add(ep)
                    else:
                        if ep_data.status_code is not None:
                            ep.status_code = ep_data.status_code
                        if ep_data.content_type is not None:
                            ep.content_type = ep_data.content_type
                        if ep_data.discovered_from is not None:
                            ep.source = ep_data.discovered_from

        # 7. Transition to Completed
        scan_job.status = ScanJobStatus.completed
        scan_job.result_json = result.model_dump_json()
        scan_job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        # 8. Transition to Failed on internal error
        scan_job.status = ScanJobStatus.failed
        scan_job.error_message = f"Scanner error: {str(e)}"
        scan_job.completed_at = datetime.utcnow()
        db.commit()

    db.refresh(scan_job)
    return scan_job

def run_scan_job_background(scan_job_id: int):
    """
    Background wrapper to safely execute a scan job using its own database session.
    """
    db = SessionLocal()
    try:
        process_scan_job(db, scan_job_id)
    except Exception as e:
        # Errors handled gracefully by process_scan_job, but catch unexpected failures here just in case.
        print(f"Background task execution aborted for Job ID {scan_job_id}: {e}")
    finally:
        db.close()
