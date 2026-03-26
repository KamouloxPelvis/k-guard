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
# Ensure the static path is absolute and clearly defined
static_path = os.path.abspath("/app/static")

@app.get("/{full_path:path}", tags=["Frontend"])
async def serve_spa(full_path: str):
    """
    Serves static files for the SPA.
    Security Implementation: Standard Path Traversal prevention using 
    absolute path validation and commonpath boundary check.
    """
    
    # 1. Construct the final physical path
    # Sanitize: Only allow alphanumeric, dots, underscores, and hyphens
    # This kills common traversal characters before they even reach path logic
    sanitized_path = "".join(c for c in full_path if c.isalnum() or c in "._-/")
    
    # Join and abspath resolve '..' and relative segments
    unsafe_path = os.path.join(static_path, sanitized_path)
    safe_path = os.path.abspath(unsafe_path)

    # 2. SECURITY BOUNDARY CHECK (The Fix for CodeQL)
    # commonpath ensures that safe_path starts with static_path.
    # If the common root of [static, safe] is not [static], an escape was attempted.
    if os.path.commonpath([static_path]) != os.path.commonpath([static_path, safe_path]):
        # Audit: Log security violation attempts here if needed
        return {"error": "Security Violation: Path escapes safe boundary"}, 403

    # 3. Serve the physical file if it exists (JS, CSS, Images)
    if os.path.isfile(safe_path):
        return FileResponse(safe_path)
    
    # 4. SPA Fallback: Serve index.html for all frontend-managed routes
    # This allows the Vue/React router to handle the URL
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    # Final fallback if even index.html is missing
    return {"error": "Requested assets could not be found"}, 404

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response