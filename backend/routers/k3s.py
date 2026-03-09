from fastapi import APIRouter, Depends, HTTPException
from k3s_manager import get_k3s_status, get_cluster_deployments, get_storage_stats, purge_trivy_cache
from .auth import verify_token

# On crée un routeur dédié à l'infrastructure K3s
router = APIRouter(tags=["K3s Infrastructure"])

@router.get("/k3s/status")
async def k3s_status(user: dict = Depends(verify_token)):
    """Expose l'état des Pods pour le Dashboard System Overview"""
    return get_k3s_status()

@router.get("/k3s/deployments/all")
async def k3s_deployments(user: dict = Depends(verify_token)):
    """Expose la liste des déploiements pour l'audit Trivy"""
    return get_cluster_deployments()

@router.get("/k3s/debug/storage")
async def k3s_storage(user: dict = Depends(verify_token)):
    """Expose les statistiques de stockage des volumes"""
    return get_storage_stats()

@router.delete("/k3s/cache/purge")
async def purge_cache(user: dict = Depends(verify_token)):
    """SRE Action: Purge le cache Trivy sur le Persistent Volume"""
    success = purge_trivy_cache()
    if success:
        return {"status": "success", "message": "Trivy cache purged successfully"}
    raise HTTPException(status_code=500, detail="Failed to purge Trivy cache")