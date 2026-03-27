from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
# Define and resolve the absolute base directory for static files once.
# Using an absolute path (/app/static) ensures consistency within the Docker container.
BASE_STATIC_DIR = Path("/app/static").resolve()

@app.get("/{rest_of_path:path}", tags=["Frontend"])
async def serve_frontend(rest_of_path: str):
    """
    Serves the Vue.js frontend with robust Path Traversal protection.
    This implementation uses explicit sanitization to satisfy static analysis tools (CodeQL).
    """
    # 1. Immediate Sanitization: Block obvious traversal attempts.
    # This explicit check helps the static analyzer recognize the path as safe.
    if ".." in rest_of_path or rest_of_path.startswith("/"):
        return JSONResponse(
            status_code=403,
            content={"error": "Security Violation: Invalid path format"},
        )

    # 2. Construct a normalized candidate path using pathlib and resolve it.
    # This removes any remaining relative segments, resolves symlinks and produces an absolute path.
    candidate_path = (BASE_STATIC_DIR / rest_of_path).resolve()

    # 3. Security Boundary Check:
    # Ensure the resolved path stays within the authorized static directory.
    is_within_base = candidate_path == BASE_STATIC_DIR or BASE_STATIC_DIR in candidate_path.parents
    if not is_within_base:
        return JSONResponse(
            status_code=403,
            content={"error": "Security Violation: Path escapes safe boundary"},
        )

    # 4. Serve physical files if they exist (assets like .js, .css, .png).
    if candidate_path.is_file():
        return FileResponse(path=candidate_path)

    # 5. SPA Fallback: Redirect all other routes to index.html.
    # This allows the Vue Router to handle client-side navigation.
    index_path = (BASE_STATIC_DIR / "index.html").resolve()
    return FileResponse(path=index_path)

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    # International standard: keep logging in English for recruiters and Cisco compliance.
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response