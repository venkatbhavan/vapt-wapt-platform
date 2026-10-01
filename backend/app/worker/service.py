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

        db.flush() # Ensure all Attack Surface entities are available for correlation queries

        # 5. Process, Normalize, Correlate, and Deduplicate Findings
        from app.models.assessment import Finding as FindingModel, FindingSeverity, Evidence as EvidenceModel, EvidenceType
        from app.risk.engine import calculate_risk
        from app.worker.correlation.correlator import correlate_finding
        from app.worker.intelligence.normalizer import normalize_finding
        from app.worker.intelligence.identity import build_identity_payload, compute_identity_hash
        from app.worker.compliance.mapper import map_finding_to_compliance

        seen_in_transaction = {}
        scanner_source_name = (getattr(result, "scanner", None) or "unknown").lower()

        for f_data in result.findings:
            severity_mapped = f_data.severity if hasattr(FindingSeverity, f_data.severity) else "info"
            confidence = getattr(f_data, 'confidence', None)

            # Temporary finding object just for correlation
            temp_finding = FindingModel(
                title=f_data.title,
                location=getattr(f_data, 'location', None)
            )

            # A. Correlate first to get attack surface context
            c_res = correlate_finding(db, assessment.id, temp_finding)
            if c_res.match_type != "none":
                temp_finding.asset_id = c_res.asset_id
                temp_finding.network_service_id = c_res.network_service_id
                temp_finding.web_application_id = c_res.web_application_id
                temp_finding.web_endpoint_id = c_res.web_endpoint_id

            # Attach objects to temp_finding for identity payload builder to access relations
            if temp_finding.web_endpoint_id:
                from app.models.attack_surface import WebEndpoint
                temp_finding.web_endpoint = db.query(WebEndpoint).get(temp_finding.web_endpoint_id)
            if temp_finding.web_application_id:
                from app.models.attack_surface import WebApplication
                temp_finding.web_application = db.query(WebApplication).get(temp_finding.web_application_id)
            if temp_finding.network_service_id:
                from app.models.attack_surface import NetworkService
                temp_finding.network_service = db.query(NetworkService).get(temp_finding.network_service_id)
            if temp_finding.asset_id:
                from app.models.attack_surface import Asset
                temp_finding.asset = db.query(Asset).get(temp_finding.asset_id)

            # B. Normalize
            intel = normalize_finding(scanner_source_name, f_data)

            # C. Identity & Deduplication
            identity_payload = build_identity_payload(assessment.id, intel["normalized_type"], temp_finding)
            identity_hash = compute_identity_hash(identity_payload)

            # Check if we already merged it in this exact scan job loop
            db_finding = seen_in_transaction.get(identity_hash)

            if not db_finding:
                # Query the database
                db_finding = db.query(FindingModel).join(ScanJob).filter(
                    ScanJob.assessment_id == assessment.id,
                    FindingModel.identity_hash == identity_hash
                ).first()

            if db_finding:
                # Merge scenario
                db_finding.updated_at = datetime.utcnow()
                sources = list(db_finding.scanner_sources or [])
                if scanner_source_name not in sources:
                    sources.append(scanner_source_name)
                    sources.sort()
                    db_finding.scanner_sources = sources

                # We do NOT arbitrarily escalate severity/confidence per requirements.
                seen_in_transaction[identity_hash] = db_finding
            else:
                # Create scenario
                risk_result = calculate_risk(severity_mapped, intel["confidence"])

                db_finding = FindingModel(
                    scan_job_id=scan_job.id,
                    title=f_data.title,
                    description=f_data.description,
                    severity=severity_mapped,
                    confidence=intel["confidence"],
                    category=intel["normalized_category"] if intel["normalized_category"] != "unknown" else getattr(f_data, 'category', None),
                    location=getattr(f_data, 'location', None),
                    impact=intel["impact"],
                    remediation=intel["remediation"],
                    risk_score=risk_result.score,
                    risk_level=risk_result.level,
                    risk_rationale=risk_result.rationale,
                    asset_id=temp_finding.asset_id,
                    network_service_id=temp_finding.network_service_id,
                    web_application_id=temp_finding.web_application_id,
                    web_endpoint_id=temp_finding.web_endpoint_id,
                    normalized_category=intel["normalized_category"],
                    normalized_type=intel["normalized_type"],
                    root_cause=intel["root_cause"],
                    exploitability_context=intel["exploitability_context"],
                    evidence_quality=intel["evidence_quality"],
                    identity_hash=identity_hash,
                    scanner_sources=[scanner_source_name]
                )
                db.add(db_finding)
                db.flush() # ensure ID is generated
                seen_in_transaction[identity_hash] = db_finding

            # Preserve Evidence always
            for e_data in f_data.evidence:
                evidence_type_mapped = e_data.evidence_type if hasattr(EvidenceType, e_data.evidence_type) else "text"
                db_evidence = EvidenceModel(
                    finding_id=db_finding.id,
                    evidence_type=evidence_type_mapped,
                    title=e_data.title,
                    content=e_data.content,
                    source=e_data.source or scanner_source_name
                )
                db.add(db_evidence)

            # E. Compliance Mapping
            map_finding_to_compliance(db, db_finding)

# 7. Transition to Completed
        scan_job.status = ScanJobStatus.completed
        scan_job.result_json = result.model_dump_json()
        scan_job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()
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
