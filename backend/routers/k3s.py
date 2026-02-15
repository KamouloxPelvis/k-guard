from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from kubernetes import client

# Imports internes
from auth import verify_token
from database import v1, apps_client
from k3s_manager import get_k3s_status, get_cluster_deployments
from metrics_manager import get_pod_metrics

# Note : On met le prefix ici pour éviter de le répéter
router = APIRouter(prefix="/k3s", tags=["K3s Monitoring"])

# --- GET HEALTH ---
@router.get("/health")
async def get_cluster_health():
    return get_k3s_status()

# --- GET CPU/RAM VPS RESOURCES ---
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
        return {"cpu_cores": 1, "memory_total_ki": 8000000}

# --- GET DEPLOYMENTS ---
@router.get("/deployments/all")    
async def list_all_deployments(user: dict = Depends(verify_token)):
    """Route de découverte pour la SecurityView (Audit Trivy)"""
    try:
        if not apps_client: return []
        
        all_deps = get_cluster_deployments()
        system_ns = ["kube-system", "kube-public", "kube-node-lease", "local-path-storage", "cert-manager", "ingress-nginx"]
        
        final_list = []
        for dep in all_deps:
            if dep['namespace'] not in system_ns:
                final_list.append({
                    "id": dep.get('id'),
                    "name": dep.get('name'),
                    "namespace": dep.get('namespace'),
                    "image": dep.get('image'),
                    "status": "Active"
                })
        return final_list
    except Exception as e:
        print(f"❌ Discovery Error: {str(e)}")
        return []

# --- GET METRICS ---
@router.get("/metrics/{namespace}")
async def get_metrics(namespace: str, user: dict = Depends(verify_token)):
    return get_pod_metrics(namespace)

# --- GET STATUS ---
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
            "cluster_version": version_info.git_version,
            "vps_os": f"{node_info.os_image} ({node_info.kernel_version})",
            "uptime": f"{uptime_delta.days} days",
            "status": "Ready" if any(c.type == 'Ready' and c.status == 'True' for c in node.status.conditions) else "NotReady"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- GET LOGS ---
@router.get("/logs/{namespace}/{pod_name}")
async def get_logs(namespace: str, pod_name: str, user: dict = Depends(verify_token)):
    try:
        if v1 is None: return {"logs": "K8s client not initialized"}
        
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        containers = [c.name for c in pod.spec.containers]
        target_container = containers[0]
        
        if len(containers) > 1:
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
