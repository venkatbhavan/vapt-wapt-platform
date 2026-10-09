import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects, assessments, scan_jobs, findings
from app.core.init_db import init_db

# Create tables
init_db()

app = FastAPI(
    title="Security Assessment Intelligence Platform API",
    description="Authorized VAPT/WAPT platform API",
    version="0.1.0"
)

# Demo Mode Middleware
import re

@app.middleware("http")
async def demo_mode_middleware(request: Request, call_next):
    if os.environ.get("DEMO_MODE") == "true":
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Exact route matching for AI analysis
            if request.method == "POST" and bool(re.match(r"^/api/assessments/\d+/ai-analysis$", request.url.path)):
                pass
            else:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Action disabled in read-only Demo Mode."}
                )
    response = await call_next(request)
    return response

# CORS configuration to allow frontend connectivity
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
allow_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(assessments.router)
app.include_router(scan_jobs.router)
app.include_router(findings.router)

from app.api import attack_surface, compliance, remediation, retests, reports, posture, ai_analyst
app.include_router(attack_surface.router)
app.include_router(compliance.router)
app.include_router(remediation.router)
app.include_router(retests.router)
app.include_router(reports.router)
app.include_router(posture.router)
app.include_router(ai_analyst.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running securely."}
