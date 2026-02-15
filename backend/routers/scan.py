from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import verify_token
from security_manager import run_trivy_scan

router = APIRouter(prefix="/scan", tags=["Security Scan"])

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