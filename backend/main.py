import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from backend import database
from fastapi import FastAPI
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# --- Routers Imports ---
from backend.network_manager import router as network_router
from backend.routers import auth, k3s, integrations, security

# --- ENV LOADING ---
# Resolve the base directory for environment configuration loading
base_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=base_dir / ".env")

app = FastAPI(
    title="🛡️ K-Guard API", 
    version="1.5.0",
    description="Backend API for K-Guard: Operational Infrastructure Security & Observability Platform",
)

# --- CORS CONFIGURATION ---
# Define allowed origins based on environment variables for security compliance
raw_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:8000,http://127.0.0.1:8000",
)
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE INITIALIZATION ---
@app.on_event("startup")
async def startup_event():
    """Triggers database initialization on application startup."""
    database.init_db()

# --- INFRASTRUCTURE ROUTES ---
@app.get("/health", tags=["Infra"])
async def liveness_probe():
    """Liveness Probe for Kubernetes/K3s health checks and monitoring."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

# --- ROUTER INCLUSION ---
app.include_router(auth.router, prefix="/api")
app.include_router(k3s.router, prefix="/api")
app.include_router(security.router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(integrations.router, prefix="/api")


# --- GLOBAL API ROUTES ---
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Application heartbeat to confirm API reachability for the frontend."""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- SECURE FRONTEND SERVING (SPA Mode) ---
BASE_STATIC_DIR = Path("/app/static").resolve()

@app.get("/{rest_of_path:path}", tags=["Frontend"])
async def serve_frontend(rest_of_path: str):
    """
    Serves the Single Page Application (SPA) index.html.
    Implements path traversal security checks to prevent unauthorized file access.
    """
    # Normalize path to prevent directory traversal attacks (e.g., ../../etc/passwd)
    requested_path = os.path.normpath(rest_of_path)
    
    # Explicitly block paths attempting to escape the base directory
    if requested_path.startswith("..") or requested_path.startswith("/"):
        return JSONResponse(status_code=403, content={"error": "Security Violation: Invalid Path"})

    # Construct and resolve the full candidate path
    candidate_path = (BASE_STATIC_DIR / requested_path).resolve()
    
    # Security check: Ensure the resolved path remains within the defined static directory
    if not str(candidate_path).startswith(str(BASE_STATIC_DIR)):
        return JSONResponse(status_code=403, content={"error": "Security Violation: Access Denied"})

    # Return the file if it exists, otherwise serve SPA index.html
    if candidate_path.is_file():
        return FileResponse(path=candidate_path)

    return FileResponse(path=(BASE_STATIC_DIR / "index.html").resolve())

# --- LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing."""
    # International standard: logs maintained in English for Cisco compliance.
    logger = logging.getLogger("K-Guard.Middleware")
    logger.info(f"Incoming {request.method} request to {request.url.path}")
    response = await call_next(request)
    return response