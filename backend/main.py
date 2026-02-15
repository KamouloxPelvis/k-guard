from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Import de tes modules existants
import auth
from routers import k3s, scan, remediation 

load_dotenv()

# On SUPPRIME root_path pour ne pas avoir de conflit avec le rewrite Nginx
app = FastAPI(
    title="🛡️ K-Guard API"
)

# --- CONFIGURATION CORS ---
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
origins += ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTAGE ---
# On utilise un router SANS préfixe supplémentaire pour que 
# les routes dans tes fichiers (k3s.router, etc.) soient directement accessibles.
# Nginx se charge déjà de supprimer le "/k-guard/api"
app.include_router(auth.router)         
app.include_router(k3s.router)          
app.include_router(scan.router)
app.include_router(remediation.router)  

# --- ROUTES DE SANTÉ (DIRECTES) ---
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "k-guard-backend"}

@app.get("/")
async def root():
    return {"message": "🛡️ K-Guard API is Online"}