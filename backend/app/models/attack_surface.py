from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.assessment import Base

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    ip_address = Column(String, nullable=False, index=True)
    hostname = Column(String, nullable=True, index=True)
    asset_type = Column(String, default="host") # "host", "container", etc.
    os = Column(String, nullable=True)
    status = Column(String, default="active")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Idempotency: Ensures unique IP per assessment.
    __table_args__ = (
        UniqueConstraint('assessment_id', 'ip_address', name='uix_assessment_ip'),
    )
    
    assessment = relationship("Assessment", back_populates="assets")
    services = relationship("NetworkService", back_populates="asset", cascade="all, delete-orphan")
    web_applications = relationship("WebApplication", back_populates="asset", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="asset")


class NetworkService(Base):
    __tablename__ = "network_services"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    port = Column(Integer, nullable=False)
    protocol = Column(String, nullable=False) # tcp, udp
    state = Column(String, nullable=False) # open, filtered, closed
    
    service_name = Column(String, nullable=True) # http, ssh
    service_product = Column(String, nullable=True) # Apache httpd
    service_version = Column(String, nullable=True) # 2.4.41
    extra_info = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Idempotency: Avoid duplicate services per asset.
    __table_args__ = (
        UniqueConstraint('asset_id', 'port', 'protocol', name='uix_asset_port_protocol'),
    )
    
    asset = relationship("Asset", back_populates="services")
    web_applications = relationship("WebApplication", back_populates="network_service")
    findings = relationship("Finding", back_populates="network_service")


class WebApplication(Base):
    __tablename__ = "web_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    network_service_id = Column(Integer, ForeignKey("network_services.id", ondelete="SET NULL"), nullable=True)
    
    base_url = Column(String, nullable=False, index=True)
    hostname = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    scheme = Column(String, nullable=False) # http, https
    
    title = Column(String, nullable=True)
    tech_info = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Idempotency: Unique base URL per asset.
    __table_args__ = (
        UniqueConstraint('asset_id', 'base_url', name='uix_asset_base_url'),
    )
    
    asset = relationship("Asset", back_populates="web_applications")
    network_service = relationship("NetworkService", back_populates="web_applications")
    endpoints = relationship("WebEndpoint", back_populates="web_application", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="web_application")


class WebEndpoint(Base):
    __tablename__ = "web_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    web_application_id = Column(Integer, ForeignKey("web_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    path = Column(String, nullable=False, index=True)
    method = Column(String, nullable=True) # GET, POST
    status_code = Column(Integer, nullable=True)
    content_type = Column(String, nullable=True)
    source = Column(String, nullable=True) # discovered by 'zap_spider', etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Idempotency: Unique path+method per web application.
    __table_args__ = (
        UniqueConstraint('web_application_id', 'path', 'method', name='uix_webapp_path_method'),
    )
    
    web_application = relationship("WebApplication", back_populates="endpoints")
    findings = relationship("Finding", back_populates="web_endpoint")
