from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path
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
# Use resolve() to ensure static_path is absolute and clean
static_path = Path("/app/static").resolve()

def _is_within_static_root(path: Path) -> bool:
    """
    Returns True if the given path is contained within the static_path directory.
    Uses Path.is_relative_to when available, otherwise falls back to relative_to.
    """
    # Python 3.9+ has Path.is_relative_to
    if hasattr(path, "is_relative_to"):
        return path.is_relative_to(static_path)  # type: ignore[attr-defined]
    try:
        path.relative_to(static_path)
        return True
    except ValueError:
        return False

@app.get("/{full_path:path}", tags=["Frontend"])
async def serve_spa(full_path: str):
    """
    Serves static files for the SPA.
    Security Implementation: Strict Path Traversal prevention using 
    absolute path validation and boundary check.
    """
    # 1. First Line of Defense: Strict Input Sanitization
    # Blocks common traversal payloads and null-byte injections
    if ".." in full_path or "\0" in full_path or full_path.startswith("/"):
        return {"error": "Security Violation: Invalid path payload"}, 400

    # 2. Safe Path Construction
    # We join and resolve to get the final absolute physical path
    requested_path = (static_path / full_path).resolve()

    # 3. Security Boundary Check (The Fix for CodeQL)
    # Ensure the resolved path is still within our static folder
    # This is a robust defense-in-depth against path traversal
    if not _is_within_static_root(requested_path):
        return {"error": "Security Violation: Path escapes safe boundary"}, 403

    # 4. Serve the physical file if it exists (JS, CSS, Images)
    if requested_path.is_file():
        # Passing the validated, absolute path as a string
        return FileResponse(str(requested_path))
    
    # 5. SPA Fallback: Serve index.html for all frontend-managed routes
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    # Security: Avoid echoing user input back to prevent XSS/Injection
    return {"error": "Requested assets could not be found"}, 404

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response