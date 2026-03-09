# SRE Patch: Forcing environment variable refresh for path resolution
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path  # Required for secure path handling
import os

import database

# Routers Imports
from network_manager import router as network_router
from routers import auth, k3s, scan, remediation, integrations

app = FastAPI(
    title="🛡️ K-Guard API", 
    version="1.0.0",
    description="Backend API for K-Guard: Operational Infrastructure Security & Automation"
)

# --- CORS CONFIGURATION ---
# Security: Restricted to origins defined in environment variables to prevent unauthorized cross-site requests.
raw_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:32726,http://127.0.0.1:32726",
)
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 0. DATABASE INITIALIZATION ---
@app.on_event("startup")
async def startup_event():
    """Triggers database initialization on application startup."""
    database.init_db()

# --- 1. INFRASTRUCTURE ROUTES ---
@app.get("/health", tags=["Infra"])
async def liveness_probe():
    """Liveness Probe for Kubernetes/K3s health checks and monitoring."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

# --- 2. ROUTER INCLUSION ---
# Logic separation: All core features are modularly organized and prefixed with /api.
app.include_router(auth.router, prefix="/api")         
app.include_router(k3s.router, prefix="/api")          
app.include_router(scan.router, prefix="/api")
app.include_router(remediation.router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(integrations.router, prefix="/api")

# --- 3. GLOBAL API ROUTES ---
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Application heartbeat to confirm API reachability for the frontend."""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- 4. SECURE FRONTEND SERVING (SPA Mode) ---
# Security: Path.resolve() ensures we use an absolute path and prevents navigation outside the static directory.
static_path = Path("/app/static").resolve()

@app.get("/{full_path:path}", tags=["Frontend"])
async def serve_spa(full_path: str):
    """
    Serves static files for the SPA.
    Security Implementation: Strictly prevents Path Traversal attacks by validating that
    the resolved requested path remains within the designated static directory.
    """
    # 1. Resolve the requested path to eliminate '../' sequences
    requested_path = (static_path / full_path).resolve()

    # 2. Path Traversal Guard: Check if the resolved path is still within static_path
    if not str(requested_path).startswith(str(static_path)):
        return {"error": "Access Denied", "path": full_path}

    # 3. Serve the physical file if it exists (JS, CSS, Images)
    if requested_path.is_file():
        return FileResponse(str(requested_path))
    
    # 4. SPA Fallback: Serve index.html for all frontend-managed routes
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    return {"error": "Frontend assets not found", "path": full_path}

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response