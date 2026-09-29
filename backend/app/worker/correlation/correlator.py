import re
import socket
import ipaddress
from typing import Optional, Tuple, List
from urllib.parse import urlparse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.attack_surface import Asset, NetworkService, WebApplication, WebEndpoint
from app.models.assessment import Finding

class CorrelationResult(BaseModel):
    asset_id: Optional[int] = None
    network_service_id: Optional[int] = None
    web_application_id: Optional[int] = None
    web_endpoint_id: Optional[int] = None
    match_type: str = "none"
    reason: str = "No deterministic correlation found."

def is_ip_address(addr: str) -> bool:
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False

def find_asset(db: Session, assessment_id: int, host_str: str) -> Optional[Asset]:
    """
    Lookup asset using Phase 6C deterministic rules.
    1. Exact IP match if host_str is an IP.
    2. Exact hostname match if host_str is a hostname.
    3. Resolved IP match if hostname resolves to an existing IP.
    """
    if not host_str:
        return None
        
    is_ip = is_ip_address(host_str)
    
    if is_ip:
        return db.query(Asset).filter(
            Asset.assessment_id == assessment_id,
            Asset.ip_address == host_str
        ).first()
    else:
        # Hostname exact match
        asset = db.query(Asset).filter(
            Asset.assessment_id == assessment_id,
            Asset.hostname == host_str
        ).first()
        if asset:
            return asset
            
        # Try resolving
        try:
            resolved_ip = socket.gethostbyname(host_str)
            return db.query(Asset).filter(
                Asset.assessment_id == assessment_id,
                Asset.ip_address == resolved_ip
            ).first()
        except Exception:
            return None

def correlate_location(db: Session, assessment_id: int, loc: str) -> CorrelationResult:
    loc = loc.strip()
    if not loc:
        return CorrelationResult()
        
    # 1. Is it a URL?
    if loc.startswith("http://") or loc.startswith("https://"):
        try:
            parsed = urlparse(loc)
            scheme = parsed.scheme.lower()
            hostname = parsed.hostname.lower() if parsed.hostname else ""
            if not hostname:
                return CorrelationResult(reason="URL missing hostname.")
                
            port = parsed.port
            if not port:
                port = 443 if scheme == "https" else 80
                
            base_url = f"{scheme}://{hostname}"
            if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
                base_url += f":{port}"
                
            path = parsed.path
            if not path:
                path = "/"
            if not path.startswith("/"):
                path = "/" + path
                
            asset = find_asset(db, assessment_id, hostname)
            if not asset:
                return CorrelationResult(reason=f"No asset found for hostname {hostname}.")
                
            svc = db.query(NetworkService).filter(
                NetworkService.asset_id == asset.id,
                NetworkService.port == port,
                NetworkService.protocol == "tcp"
            ).first()
            
            if not svc:
                return CorrelationResult(
                    asset_id=asset.id, 
                    match_type="asset", 
                    reason="Matched Asset, but NetworkService not found."
                )
                
            app = db.query(WebApplication).filter(
                WebApplication.asset_id == asset.id,
                WebApplication.base_url == base_url
            ).first()
            
            if not app:
                return CorrelationResult(
                    asset_id=asset.id,
                    network_service_id=svc.id,
                    match_type="service",
                    reason="Matched NetworkService, but WebApplication not found."
                )
                
            # Endpoint resolution
            # We don't have the method, so we search by path.
            endpoints = db.query(WebEndpoint).filter(
                WebEndpoint.web_application_id == app.id,
                WebEndpoint.path == path
            ).all()
            
            if len(endpoints) == 1:
                return CorrelationResult(
                    asset_id=asset.id,
                    network_service_id=svc.id,
                    web_application_id=app.id,
                    web_endpoint_id=endpoints[0].id,
                    match_type="endpoint",
                    reason="Exact normalized URL matched unique WebEndpoint."
                )
            elif len(endpoints) > 1:
                return CorrelationResult(
                    asset_id=asset.id,
                    network_service_id=svc.id,
                    web_application_id=app.id,
                    match_type="application",
                    reason="Normalized application URL matched, but HTTP method was unavailable and multiple endpoints exist."
                )
            else:
                return CorrelationResult(
                    asset_id=asset.id,
                    network_service_id=svc.id,
                    web_application_id=app.id,
                    match_type="application",
                    reason="Matched WebApplication, but WebEndpoint not found."
                )
                
        except Exception as e:
            return CorrelationResult(reason=f"URL parsing failed: {str(e)}")

    # 2. Is it an Nmap service location? (e.g., 127.0.0.1:443/tcp)
    nmap_match = re.match(r"^([^:]+):(\d+)/(tcp|udp)$", loc, re.IGNORECASE)
    if nmap_match:
        host_str = nmap_match.group(1)
        port = int(nmap_match.group(2))
        proto = nmap_match.group(3).lower()
        
        asset = find_asset(db, assessment_id, host_str)
        if not asset:
            return CorrelationResult(reason=f"No asset found for {host_str}.")
            
        svc = db.query(NetworkService).filter(
            NetworkService.asset_id == asset.id,
            NetworkService.port == port,
            NetworkService.protocol == proto
        ).first()
        
        if svc:
            return CorrelationResult(
                asset_id=asset.id,
                network_service_id=svc.id,
                match_type="service",
                reason="Exact IP, port, and protocol matched NetworkService."
            )
        else:
            return CorrelationResult(
                asset_id=asset.id,
                match_type="asset",
                reason="Matched Asset, but NetworkService not found."
            )

    # 3. Is it just a host?
    asset = find_asset(db, assessment_id, loc)
    if asset:
        return CorrelationResult(
            asset_id=asset.id,
            match_type="asset",
            reason="Exact host matched Asset."
        )

    return CorrelationResult()

def correlate_finding(db: Session, assessment_id: int, finding: Finding) -> CorrelationResult:
    """
    Determines the best correlation for a finding.
    If multiple locations exist, it correlates based on the first location,
    but gracefully downgrades if they don't share the same hierarchy.
    """
    if not finding.location:
        return CorrelationResult()
        
    locations = [l.strip() for l in finding.location.split(",") if l.strip()]
    if not locations:
        return CorrelationResult()
        
    # Correlate based on the first location
    # If a finding lists multiple locations, we could find the common denominator, 
    # but for simplicity and strictness, if they disagree, we should probably downgrade.
    # However, ZAP findings group identical alerts on multiple URLs of the SAME app.
    
    first_res = correlate_location(db, assessment_id, locations[0])
    
    if len(locations) == 1 or first_res.match_type == "none":
        return first_res
        
    # Verify consistency across other locations to prevent ambiguous false links
    shared_asset = first_res.asset_id
    shared_svc = first_res.network_service_id
    shared_app = first_res.web_application_id
    shared_ep = first_res.web_endpoint_id
    
    for loc in locations[1:]:
        res = correlate_location(db, assessment_id, loc)
        
        if res.asset_id != shared_asset:
            shared_asset = None
            shared_svc = None
            shared_app = None
            shared_ep = None
            break
            
        if res.network_service_id != shared_svc:
            shared_svc = None
            shared_app = None
            shared_ep = None
            
        if res.web_application_id != shared_app:
            shared_app = None
            shared_ep = None
            
        if res.web_endpoint_id != shared_ep:
            shared_ep = None

    # Reconstruct downgraded result
    if shared_ep:
        return CorrelationResult(
            asset_id=shared_asset, network_service_id=shared_svc, 
            web_application_id=shared_app, web_endpoint_id=shared_ep,
            match_type="endpoint", reason="All locations matched WebEndpoint."
        )
    elif shared_app:
        return CorrelationResult(
            asset_id=shared_asset, network_service_id=shared_svc, 
            web_application_id=shared_app,
            match_type="application", reason="Multiple locations mapped to same WebApplication."
        )
    elif shared_svc:
        return CorrelationResult(
            asset_id=shared_asset, network_service_id=shared_svc, 
            match_type="service", reason="Multiple locations mapped to same NetworkService."
        )
    elif shared_asset:
        return CorrelationResult(
            asset_id=shared_asset, 
            match_type="asset", reason="Multiple locations mapped to same Asset."
        )
        
    return CorrelationResult(reason="Locations mapped to entirely different assets. Correlation aborted.")
