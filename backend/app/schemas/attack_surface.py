from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# ----------------------------------------
# Findings (Attack Surface Scope)
# ----------------------------------------
class AttackSurfaceFinding(BaseModel):
    id: int
    title: str
    severity: str
    confidence: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    status: str
    category: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------
# Endpoints
# ----------------------------------------
class WebEndpointBase(BaseModel):
    path: str
    method: Optional[str] = None
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    source: Optional[str] = None

class WebEndpointCreate(WebEndpointBase):
    pass

class WebEndpointResponse(WebEndpointBase):
    id: int
    web_application_id: int
    created_at: datetime
    updated_at: datetime
    findings: List[AttackSurfaceFinding] = []

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------
# Web Applications
# ----------------------------------------
class WebApplicationBase(BaseModel):
    base_url: str
    hostname: Optional[str] = None
    port: Optional[int] = None
    scheme: str
    title: Optional[str] = None
    tech_info: Optional[str] = None

class WebApplicationCreate(WebApplicationBase):
    network_service_id: Optional[int] = None

class WebApplicationResponse(WebApplicationBase):
    id: int
    asset_id: int
    network_service_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    endpoints: List[WebEndpointResponse] = []
    findings: List[AttackSurfaceFinding] = []

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------
# Network Services
# ----------------------------------------
class NetworkServiceBase(BaseModel):
    port: int
    protocol: str
    state: str
    service_name: Optional[str] = None
    service_product: Optional[str] = None
    service_version: Optional[str] = None
    extra_info: Optional[str] = None

class NetworkServiceCreate(NetworkServiceBase):
    pass

class NetworkServiceResponse(NetworkServiceBase):
    id: int
    asset_id: int
    created_at: datetime
    updated_at: datetime
    web_applications: List[WebApplicationResponse] = []
    findings: List[AttackSurfaceFinding] = []

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------
# Assets
# ----------------------------------------
class AssetBase(BaseModel):
    ip_address: str
    hostname: Optional[str] = None
    asset_type: str = "host"
    os: Optional[str] = None
    status: str = "active"

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    assessment_id: int
    created_at: datetime
    updated_at: datetime
    services: List[NetworkServiceResponse] = []
    web_applications: List[WebApplicationResponse] = []
    findings: List[AttackSurfaceFinding] = []

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------
# Root Response
# ----------------------------------------
class AttackSurfaceRootResponse(BaseModel):
    assessment_id: int
    assets: List[AssetResponse] = []
