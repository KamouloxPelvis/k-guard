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
from backend.routers import auth, k3s, scan, remediation, integrations, sentinel_test

print(f"DEBUG: LE MODULE EST CHARGÉ DEPUIS : {sentinel_test.__file__}")


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
app.include_router(sentinel_test.router, prefix="/api")

# --- 3. GLOBAL API ROUTES ---
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Application heartbeat to confirm API reachability for the frontend."""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- 4. SECURE FRONTEND SERVING (SPA Mode) ---
root_path = os.getenv("PROJECT_ROOT", "/home/kamal/infrastructure/apps/k-guard")
BASE_STATIC_DIR = (Path(root_path) / "frontend" / "dist").resolve()

@app.get("/{rest_of_path:path}", tags=["Frontend"])
async def serve_frontend(rest_of_path: str):
    """
    Serves the Vue.js frontend with robust Path Traversal protection.
    Optimized for CodeQL static analysis recognition.
    """
    # 1. Validation & Normalization
    # We resolve the path immediately to neutralize '..' and symlinks.
    candidate_path = (BASE_STATIC_DIR / rest_of_path).resolve()

    # 2. Strict Boundary Check
    # CodeQL prefers direct comparison or .relative_to() within the final check.
    try:
        # This check is the gold standard for Path Traversal prevention in Python.
        # It raises a ValueError if candidate_path is not under BASE_STATIC_DIR.
        candidate_path.relative_to(BASE_STATIC_DIR)
    except (ValueError, RuntimeError):
        return JSONResponse(
            status_code=403,
            content={"error": "Security Violation: Path escapes safe boundary"},
        )

    # 3. File existence check
    if candidate_path.is_file():
        # Passing the Path object directly is the secure standard for FastAPI/Starlette.
        return FileResponse(path=candidate_path)

    # 4. SPA Fallback
    index_path = BASE_STATIC_DIR / "index.html"
    return FileResponse(path=index_path.resolve())

# --- 5. LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware for request tracing and security auditing of incoming traffic."""
    # International standard: keep logging in English for recruiters and Cisco compliance.
    print(f"DEBUG: {request.method} request to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response
