from database import v1, apps_client
import shutil
import os

# Namespaces to exclude from security monitoring and dashboard
SYSTEM_NS = ["kube-system", "kube-public", "kube-node-lease", "local-path-storage", "cert-manager", "ingress-nginx"]

def get_k3s_status():
    """Retrieves Pod health status for the Dashboard visualization."""
    if not v1:
        print("⚠️ K8s Client (v1) not initialized")
        return []
    
    pod_results = []
    try:
        # Scan all namespaces (authorized by ClusterRole RBAC)
        pods = v1.list_pod_for_all_namespaces(watch=False)
        for pod in pods.items:
            ns = pod.metadata.namespace
            
            if ns not in SYSTEM_NS:
                # 1. Handle display name vs. unique technical name
                app_label = pod.metadata.labels.get('app')
                display_name = app_label if app_label else pod.metadata.name.split('-')[0]
                
                # 2. Intelligent status mapping to avoid false alarms
                phase = pod.status.phase
                if phase == "Running":
                    status_label = "SECURE"
                elif phase == "Pending":
                    status_label = "STABILIZING" # Less alarming than ALERT for scaling/updates
                else:
                    status_label = "ALERT"

                pod_results.append({
                    "name": display_name,         # UI Display name
                    "pod_name": pod.metadata.name, # Unique identifier for logs/actions
                    "namespace": ns,
                    "status": status_label,
                    "ip": pod.status.pod_ip or "N/A",
                    "type": "k3s Pod",
                    "creation": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                })
        return pod_results 
    except Exception as e:
        print(f"❌ Health Status Error: {e}")
        return []

def get_cluster_deployments():
    """Retrieves deployments for security auditing (Trivy discovery)."""
    if not apps_client:
        print("⚠️ K8s AppsClient not initialized")
        return []
        
    try:
        deps = apps_client.list_deployment_for_all_namespaces()
        app_list = []
        for dep in deps.items:
            ns = dep.metadata.namespace
            if ns not in SYSTEM_NS:
                # Retrieve the image of the first container (standard for our app architecture)
                container_image = dep.spec.template.spec.containers[0].image
                
                app_list.append({
                    "id": dep.metadata.uid,
                    "name": dep.metadata.name,
                    "namespace": ns,
                    "image": container_image,
                    "status": "Active" 
                })
        return app_list
    except Exception as e:
        print(f"❌ Discovery Error: {e}")
        return []

def get_storage_stats():
    """Checks disk space on critical mount points (PVC / Root)."""
    paths = ["/", "/data/trivy-cache", "/app"]
    stats = {}
    
    for path in paths:
        if os.path.exists(path):
            total, used, free = shutil.disk_usage(path)
            stats[path] = {
                "total_gb": round(total / (2**30), 2),
                "used_gb": round(used / (2**30), 2),
                "free_gb": round(free / (2**30), 2),
                "percent": round((used / total) * 100, 1)
            }
    return stats

def purge_trivy_cache():
    """Safely removes Trivy cache content on the Persistent Volume (PVC)."""
    cache_path = "/data/trivy-cache"
    try:
        if os.path.exists(cache_path):
            # Clear directory content without deleting the root folder (mount point)
            for filename in os.listdir(cache_path):
                file_path = os.path.join(cache_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            return True
        return False
    except Exception as e:
        print(f"❌ Purge Error: {e}")
        return False

def get_pod_logs(namespace: str, pod_name: str):
    """
    SRE Feature: Retrieves the last 50 lines of logs for a specific pod.
    """
    if not v1:
        return "⚠️ K8s Client not initialized."
    try:
        # Fetching logs with a tail limit to prevent heavy payload transfers
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=50)
        return logs
    except Exception as e:
        print(f"❌ Log Retrieval Error: {str(e)}")
        return f"CRITICAL ERROR: Unable to retrieve logs for {pod_name}."