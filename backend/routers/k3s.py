import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from backend.k3s_manager import (
    get_k3s_status, 
    get_cluster_deployments, 
    get_storage_stats, 
    get_node_capacity,
    get_pod_logs
)
from backend.metrics_manager import get_pod_metrics 
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

@router.get("/k3s/cluster-status")
async def k3s_status(user: dict = Depends(verify_token)):
    """
    Provides an inventory of Pod health status for the System Overview dashboard.
    """
    return get_k3s_status()

@router.get("/k3s/status")
async def get_vps_specs(user: dict = Depends(verify_token)):
    """
    Retrieves host OS and K3s version dynamically from the nodes.
    Powers the system metadata footer.
    """
    try:
        from kubernetes import client
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        if not nodes.items:
            return {"cluster_version": "Unknown", "vps_os": "Linux Host"}
            
        node = nodes.items[0]
        return {
            "cluster_version": node.status.node_info.kubelet_version,
            "vps_os": node.status.node_info.os_image,
            "uptime": "Active",
            "status": "Online"
        }
    except Exception as e:
        return {"cluster_version": "v1.28-k3s", "vps_os": "Generic Linux"}

@router.get("/k3s/deployments/all")
async def k3s_deployments(user: dict = Depends(verify_token)):
    """
    Discovers all active deployments for security auditing and inventory purposes.
    """
    return get_cluster_deployments()

@router.get("/k3s/debug/storage")
async def k3s_storage(user: dict = Depends(verify_token)):
    """
    Aggregates SRE storage statistics. 
    Conforms to the 'DebugInfo' Frontend interface.
    """
    # Fetch filesystem usage statistics via SRE utility
    disks = get_storage_stats()
    
    # Return a standardized payload for the Settings dashboard
    return {
        "status": "online",
        "disks": disks,
        "timestamp": datetime.utcnow().isoformat()
    }