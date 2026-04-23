import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from k3s_manager import (
    get_k3s_status, 
    get_cluster_deployments, 
    get_storage_stats, 
    purge_trivy_cache, 
    get_node_capacity,
    get_pod_logs
)
from metrics_manager import get_pod_metrics 
from .auth import verify_token

# Dedicated router for K3s Infrastructure management and monitoring
router = APIRouter(tags=["K3s Infrastructure"])

@router.get("/k3s/metrics/{namespace}")
async def k3s_metrics(namespace: str, user: dict = Depends(verify_token)):
    """
    Exposes real-time CPU and RAM metrics fetched from the K8s Metrics Server API.
    Used by HealthView.vue for resource utilization charts.
    """
    return get_pod_metrics(namespace=namespace)

@router.get("/k3s/logs/{namespace}/{pod_name}")
async def k3s_pod_logs(namespace: str, pod_name: str, user: dict = Depends(verify_token)):
    """
    Fetches real-time terminal stdout/stderr logs for the SRE secure console modal.
    """
    logs = get_pod_logs(namespace, pod_name)
    return {"logs": logs}

@router.get("/k3s/node-capacity")
async def node_capacity(user: dict = Depends(verify_token)):
    """
    Retrieves physical VPS hardware limits (CPU/RAM) to calculate percentage metrics on Frontend.
    """
    return get_node_capacity()

@router.get("/k3s/status")
async def k3s_status(user: dict = Depends(verify_token)):
    """
    Provides an inventory of Pod health status for the System Overview dashboard.
    """
    return get_k3s_status()

@router.get("/k3s/deployments/all")
async def k3s_deployments(user: dict = Depends(verify_token)):
    """
    Discovers all active deployments for automated Trivy security auditing.
    """
    return get_cluster_deployments()

@router.get("/k3s/debug/storage")
async def k3s_storage(user: dict = Depends(verify_token)):
    """
    Aggregates SRE storage statistics and K-Guard/Trivy database persistence status.
    Conforms to the 'DebugInfo' Frontend interface.
    """
    # 1. Fetch filesystem usage statistics via SRE utility
    disks = get_storage_stats()
    
    # 2. Verify database persistence on the Persistent Volume (PVC)
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    db_exists = os.path.exists(os.path.join(cache_path, "db"))
    
    # 3. Return a standardized payload for the Settings dashboard
    return {
        "status": "online",
        "disks": disks,
        "database_present": db_exists,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.delete("/k3s/cache/purge")
async def purge_cache(user: dict = Depends(verify_token)):
    """
    SRE Maintenance: Safely wipes the Trivy local databases from the Persistent Volume.
    """
    success = purge_trivy_cache()
    if success:
        return {"status": "success", "message": "Trivy cache purged successfully"}
    
    # Security best practice: Avoid revealing internal path details in the exception
    raise HTTPException(status_code=500, detail="SRE Action Failed: Unable to purge persistent cache.")