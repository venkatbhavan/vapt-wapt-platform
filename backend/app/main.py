from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend is running securely."}
