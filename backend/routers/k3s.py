from fastapi import APIRouter, Depends
from k3s_manager import get_k3s_status, get_cluster_deployments, get_storage_stats
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