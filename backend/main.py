import os
from dotenv import load_dotenv
from pathlib import Path
from backend import database
from fastapi import FastAPI, APIRouter
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
#from prometheus_fastapi_instrumentator import Instrumentator

# --- Routers Imports ---
from backend.network_manager import router as network_router
from backend.routers import auth, k3s, scan, remediation, integrations

# --- ENV LOADING ---
base_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=base_dir / ".env")

app = FastAPI(
    title="🛡️ K-Guard API", 
    version="1.0.0",
    description="Backend API for K-Guard: Operational Infrastructure Security & Automation"
)


#instrumentator = Instrumentator(should_group_status_codes=True)

#instrumentator.instrument(app, metric_namespace="kguard").expose(app)

# --- CORS CONFIGURATION ---
# Security: Restricted to origins defined in environment variables to prevent unauthorized cross-site requests.
raw_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:8443,http://127.0.0.1:8443",
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
# Define the absolute path to static assets within the container.
# This ensures consistency regardless of the current working directory.
BASE_STATIC_DIR = Path("/app/static").resolve()

@app.get("/{rest_of_path:path}", tags=["Frontend"])
async def serve_frontend(rest_of_path: str):
    """
    Serves the Single Page Application (SPA) index.html for any requested path.
    Implements security checks to prevent path traversal attacks.
    """
    # If the path is empty, default to index.html
    if not rest_of_path:
        rest_of_path = "index.html"
    
    # Resolve the requested path relative to the static directory
    candidate_path = (BASE_STATIC_DIR / rest_of_path).resolve()
    
    # Security: Ensure the file remains within the designated static directory
    try:
        candidate_path.relative_to(BASE_STATIC_DIR)
    except ValueError:
        return JSONResponse(status_code=403, content={"error": "Security Violation"})

    # Check if the requested file exists
    if candidate_path.is_file():
        return FileResponse(path=candidate_path)

    # SPA Fallback: If the file is not found (e.g., client-side route), serve index.html
    return FileResponse(path=(BASE_STATIC_DIR / "index.html").resolve())

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    # International standard: keep logging in English for recruiters and Cisco compliance.
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response
