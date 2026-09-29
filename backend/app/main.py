from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects, assessments, scan_jobs, findings
from app.models.assessment import Base
import app.models.attack_surface  # Ensure Attack Surface models are loaded before create_all
from app.core.database import engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Security Assessment Intelligence Platform API",
    description="Authorized VAPT/WAPT platform API",
    version="0.1.0"
)

# CORS configuration to allow frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # React/Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(assessments.router)
app.include_router(scan_jobs.router)
app.include_router(findings.router)

from app.api import attack_surface
app.include_router(attack_surface.router)




@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running securely."}
