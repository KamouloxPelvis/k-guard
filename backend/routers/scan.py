import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .auth import verify_token
from security_manager import run_trivy_scan

router = APIRouter(prefix="/scan", tags=["Security Scan"])

@router.get("/debug-storage")
async def debug_storage(user: dict = Depends(verify_token)):
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    try:
        # On liste le contenu du dossier de cache
        files = []
        if os.path.exists(cache_path):
            files = os.listdir(cache_path)
            # On vérifie si le sous-dossier 'db' existe (créé par Trivy)
            db_exists = os.path.exists(os.path.join(cache_path, "db"))
        else:
            return {"error": f"Le dossier {cache_path} n'existe pas."}

        return {
            "mount_path": cache_path,
            "owner_uid": os.stat(cache_path).st_uid,
            "content": files,
            "trivy_db_initialized": db_exists,
            "message": "Si 'db' est présent, la persistance est opérationnelle !"
        }
    except Exception as e:
        return {"error": str(e)}

class ScanRequest(BaseModel):
    image: str

@router.post("/scan")
async def security_scan(payload: ScanRequest, user: dict = Depends(verify_token)):
    """
    Lance un audit Trivy sur une image spécifique.
    Nécessite le montage du docker.sock dans le déploiement K3s.
    """
    try:
        # payload.image est maintenant validé par Pydantic
        return run_trivy_scan(payload.image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du scan : {str(e)}")