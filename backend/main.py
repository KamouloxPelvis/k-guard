from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime

import database
import os

# Imports des routeurs
from routers import auth, k3s, scan, remediation

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
@app.get("/", tags=["Root"])
async def root():
    return {"message": "🛡️ K-Guard API is running. Access via /api"}

@app.get("/health", tags=["Infra"])
async def liveness_probe():
    """Liveness pour K3s (Probe)"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# --- 2. INCLUSION DES ROUTEURS ---
app.include_router(auth.router, prefix="/api")         
app.include_router(k3s.router, prefix="/api")          
app.include_router(scan.router, prefix="/api")
app.include_router(remediation.router, prefix="/api")


# --- 3. ROUTES API GLOBALES (Post-Inclusion) ---
# Spécifique au Frontend, passe par Nginx via /api/health
@app.get("/api/health", tags=["Status"])
async def api_heartbeat():
    """Heartbeat pour le Frontend Vue.js"""
    return {"status": "online", "message": "K-Guard API is reachable"}

# --- 4. SERVIR LE FRONTEND (À la toute fin) ---
static_path = "/app/static" # On définit la variable ICI

if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
    print(f"✅ Frontend monté depuis {static_path}")
else:
    print(f"⚠️ Warning: Frontend directory not found at {static_path}")