import os
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from kubernetes import client

# Internal imports
from .auth import verify_token
from database import v1, apps_client, DB_PATH
from k3s_manager import get_k3s_status, get_cluster_deployments, get_storage_stats
from metrics_manager import get_pod_metrics

router = APIRouter(prefix="/k3s", tags=["K3s Monitoring"])

@router.get("/health")
async def k3s_module_health(user: dict = Depends(verify_token)):
    return {"status": "ok", "service": "k3s-manager"}

@router.get("/cluster-status")
async def get_cluster_health(user: dict = Depends(verify_token)):
    return get_k3s_status()

@router.get("/node-capacity")
async def get_node_capacity(user: dict = Depends(verify_token)):
    try:
        nodes = v1.list_node()
        node = nodes.items[0]
        capacity = node.status.capacity
        return {
            "cpu_cores": int(capacity.get("cpu", 1)),
            "memory_total_ki": int(capacity.get("memory", "0").replace("Ki", ""))
        }
    except Exception:
        # Default fallback values if Node API is unreachable
        return {"cpu_cores": 1, "memory_total_ki": 8000000}

@router.get("/deployments/all")    
async def list_all_deployments(user: dict = Depends(verify_token)):
    """Discovery route for SecurityView (Trivy Audit)"""
    try:
        if not apps_client: return []
        all_deps = get_cluster_deployments()
        # Filter out system namespaces to focus on user applications
        system_ns = ["kube-system", "kube-public", "kube-node-lease", "local-path-storage", "cert-manager", "ingress-nginx"]
        
        return [
            {
                "id": dep.get('id'),
                "name": dep.get('name'),
                "namespace": dep.get('namespace'),
                "image": dep.get('image'),
                "status": "Active"
            } for dep in all_deps if dep['namespace'] not in system_ns
        ]
    except Exception as e:
        print(f"❌ Discovery Error: {str(e)}")
        return []

@router.get("/metrics/{namespace}")
async def get_metrics(namespace: str, user: dict = Depends(verify_token)):
    try:
        data = get_pod_metrics(namespace)
        # Force return as list even if metrics manager returns None
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"🚨 Metrics Error: {e}")
        return [] # Prevents Frontend crash during .map() operations

@router.get("/status")
async def get_cluster_status(user: dict = Depends(verify_token)):
    try:
        if not v1: raise HTTPException(status_code=500, detail="K8s client not initialized")
        version_info = client.VersionApi().get_code()
        nodes = v1.list_node()
        if not nodes.items: return {"status": "Error", "detail": "No nodes found"}
        
        node = nodes.items[0]
        node_info = node.status.node_info
        creation_time = node.metadata.creation_timestamp
        uptime_delta = datetime.utcnow().replace(tzinfo=None) - creation_time.replace(tzinfo=None)
        
        return {
            "cluster_version": getattr(version_info, 'git_version', "Unknown"),
            "vps_os": f"{getattr(node_info, 'os_image', 'Unknown OS')}",
            "uptime": f"{uptime_delta.days} days",
            "status": "Ready" if any(c.type == 'Ready' and c.status == 'True' for c in node.status.conditions) else "NotReady"
        }
    except Exception as e:
        # Crucial: Return object with consistent keys to prevent Frontend crashes
        return {
            "cluster_version": "N/A",
            "vps_os": "Error checking OS",
            "uptime": "0 days",
            "status": "Error"
        }

@router.get("/logs/{namespace}/{pod_name}")
async def get_logs(namespace: str, pod_name: str, user: dict = Depends(verify_token)):
    try:
        if v1 is None: return {"logs": "K8s client not initialized"}
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        containers = [c.name for c in pod.spec.containers]
        target_container = containers[0]
        
        # Heuristic to find the main application container
        for c_name in containers:
            if any(k in c_name.lower() for k in ["backend", "app", "api", "server"]):
                target_container = c_name
                break

        logs = v1.read_namespaced_pod_log(
            name=pod_name, namespace=namespace, container=target_container, tail_lines=100
        )
        return {"logs": logs}
    except Exception as e:
        return {"logs": f"ERROR: {str(e)}"}

@router.get("/debug/storage")
async def debug_storage(user: dict = Depends(verify_token)):
    """SRE diagnostic route for storage health"""
    try:
        stats = get_storage_stats()
        # Verify SQLite database accessibility
        db_exists = os.path.exists(DB_PATH)
        
        return {
            "status": "success",
            "disks": stats,
            "database_present": db_exists,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
@router.post("/debug/purge-cache")
async def action_purge_cache(user: dict = Depends(verify_token)):
    """Maintenance action to free up PVC space"""
    success = purge_trivy_cache()
    if success:
        return {"status": "success", "message": "Trivy cache successfully purged."}
    else:
        raise HTTPException(status_code=500, detail="Failed to purge cache.")