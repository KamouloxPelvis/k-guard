from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import database

# Imports des routeurs (via le package routers)
from routers import auth, k3s, scan, remediation

app = FastAPI(title="🛡️ K-Guard API", version="1.5.0")

# --- CONFIGURATION ---
API_PREFIX = "/api"

api_router = APIRouter()

# --- CONFIGURATION CORS ---
raw_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:32726,http://127.0.0.1:32726"
)

# On transforme la chaîne "url1,url2" en une vraie liste Python ["url1", "url2"]
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Route de santé ROOT (Pour les Probes Kubernetes)
@app.get("/health")
async def liveness_probe():
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# --- INCLUSION DES ROUTEURS ---
api_router.include_router(auth.router)         
api_router.include_router(k3s.router)          
api_router.include_router(scan.router)
api_router.include_router(remediation.router)

app.include_router(api_router, prefix=API_PREFIX)

# ✅ Route de santé API (Pour le Frontend)
@api_router.get("/health")
async def api_health():
    return {"status": "online"}

@app.get("/")
async def root():
    return {"message": "🛡️ K-Guard API is running. Access via /api"}