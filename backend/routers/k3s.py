import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from k3s_manager import get_k3s_status, get_cluster_deployments, get_storage_stats, purge_trivy_cache
from .auth import verify_token

# On crée un routeur dédié à l'infrastructure K3s
router = APIRouter(tags=["K3s Infrastructure"])

@router.get("/k3s/cluster-status")
async def k3s_status(user: dict = Depends(verify_token)):
    """Expose l'état des Pods pour le Dashboard System Overview"""
    return get_k3s_status()

@router.get("/k3s/deployments/all")
async def k3s_deployments(user: dict = Depends(verify_token)):
    """Expose la liste des déploiements pour l'audit Trivy"""
    return get_cluster_deployments()

@router.get("/k3s/debug/storage")
async def k3s_storage(user: dict = Depends(verify_token)):
    """Expose les statistiques de stockage et l'état de la base de données K-Guard/Trivy"""
    # 1. Récupération des statistiques disques SRE
    disks = get_storage_stats()
    
    # 2. Vérification de la persistance (Base de données)
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    db_exists = os.path.exists(os.path.join(cache_path, "db"))
    
    # 3. Formatage de la réponse conforme à l'interface Frontend 'DebugInfo'
    return {
        "status": "online",
        "disks": disks,
        "database_present": db_exists,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.delete("/k3s/cache/purge")
async def purge_cache(user: dict = Depends(verify_token)):
    """SRE Action: Purge le cache Trivy sur le Persistent Volume"""
    success = purge_trivy_cache()
    if success:
        return {"status": "success", "message": "Trivy cache purged successfully"}
    raise HTTPException(status_code=500, detail="Failed to purge Trivy cache")