from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime

import database
import os

# Routers Imports
from network_manager import router as network_router
from routers import auth, k3s, scan, remediation, integrations

app = FastAPI(title="🛡️ K-Guard API", version="1.5.0")

# --- CORS CONFIGURATION ---
# Load allowed origins from environment (defaults to common local ports)
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

# --- 0. Database Initialization ---
@app.on_event("startup")
async def startup_event():
    """Triggers database initialization on application startup"""
    database.init_db()

# --- 1. INFRASTRUCTURE ROUTES (Outside API Prefix) ---
@app.get("/health", tags=["Infra"])
async def liveness_probe():
    """Liveness Probe for K3s/Kubernetes health checks"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# --- 2. ROUTER INCLUSION ---
# All core logic is prefixed with /api for clean routing
app.include_router(auth.router, prefix="/api")         
app.include_router(k3s.router, prefix="/api")          
app.include_router(scan.router, prefix="/api")
app.include_router(remediation.router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
    

# --- 3. GLOBAL API ROUTES (Post-Inclusion) ---
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Heartbeat endpoint for the Frontend (Vue.js/React)"""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- 4. SERVING FRONTEND (SPA Mode) ---
static_path = "/app/static"

@app.get("/{full_path:path}", tags=["Frontend"])
async def serve_spa(full_path: str):
    """
    Serves static files if they exist, otherwise returns index.html.
    This lightweight approach handles SPA routing without conflicts.
    """
    file_path = os.path.join(static_path, full_path)
    
    # If a physical file exists (JS/CSS/Image), serve it directly
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For all other routes (Frontend routing), serve index.html
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    return {"error": "Frontend not found", "path": full_path}

# --- 5. VERBOSE DEBUG MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request, call_next):
    """Debug middleware to trace incoming traffic and response codes"""
    print(f"DEBUG: Incoming {request.method} to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response