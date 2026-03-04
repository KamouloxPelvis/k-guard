from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime

import database
import os

# Imports des routeurs
from network_manager import router as network_router
from routers import auth, k3s, scan, remediation, integrations

app = FastAPI(title="🛡️ K-Guard API", version="1.5.0")

# --- CONFIGURATION CORS ---
raw_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:32726,http://127.0.0.1:32726"
)
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 0. Initialisation de la base de données Scans ---
@app.on_event("startup")
async def startup_event():
    database.init_db()

# --- 1. ROUTES INFRA (Hors API Prefix) ---
# @app.get("/", tags=["Root"])
# async def root():
#     return {"message": "🛡️ K-Guard API is running. Access via /api"}

@app.get("/health", tags=["Infra"])
async def liveness_probe():
    """Liveness pour K3s (Probe)"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# --- 2. INCLUSION DES ROUTEURS ---
app.include_router(auth.router, prefix="/api")         
app.include_router(k3s.router, prefix="/api")          
app.include_router(scan.router, prefix="/api")
app.include_router(remediation.router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
    

# --- 3. ROUTES API GLOBALES (Post-Inclusion) ---
# Spécifique au Frontend, passe par Nginx via /api/health
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Heartbeat pour le Frontend Vue.js"""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- 4. SERVIR LE FRONTEND (Version stabilisée) ---
static_path = "/app/static"

@app.get("/{full_path:path}", tags=["Frontend"])
async def serve_spa(full_path: str):
    """
    Sert les fichiers statiques s'ils existent, sinon renvoie index.html.
    C'est plus léger et évite les conflits avec app.mount.
    """
    file_path = os.path.join(static_path, full_path)
    
    # Si c'est un fichier JS/CSS/Image réel, on le sert
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Pour tout le reste (routage Vue), on sert l'index
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    return {"error": "Frontend not found", "path": full_path}

# --- 5. MIDDLEWARE MODE 'VERBEUX'---
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"DEBUG: Incoming {request.method} to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response