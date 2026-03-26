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
# Define and resolve the absolute base directory for static files once
# This ensures we have a reliable reference point for the security boundary.
BASE_STATIC_DIR = Path("/app/static").resolve()

@app.get("/{rest_of_path:path}", tags=["Frontend"])
async def serve_frontend(rest_of_path: str):
    """
    Serves the Vue.js frontend with robust Path Traversal protection.
    """
    # 1. Construct and resolve the target path
    # Path.joinpath() handles the OS-specific separators correctly.
    target_path = BASE_STATIC_DIR.joinpath(rest_of_path).resolve()

    # 2. Security Boundary Check
    # We compare the resolved target path against the authorized base directory.
    # This effectively neutralizes ".." or symlink attacks.
    if not str(target_path).startswith(str(BASE_STATIC_DIR)):
        return {"error": "Security Violation: Path escapes safe boundary"}, 403

    # 3. Serve physical files if they exist (assets like .js, .css, .png)
    if target_path.is_file():
        return FileResponse(str(target_path))

    # 4. SPA Fallback: Redirect all other routes to index.html
    # This allows the Vue Router to handle the URL on the client side.
    index_path = BASE_STATIC_DIR.joinpath("index.html")
    return FileResponse(str(index_path))

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response