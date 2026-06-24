from backend.database import v1, apps_client
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
        pods = v1.list_pod_for_all_namespaces(watch=False)
        for pod in pods.items:
            ns = pod.metadata.namespace
            
            if ns not in SYSTEM_NS:
                # 1. Smart Name Formatting: Prioritize explicit K8s labels
                app_label = pod.metadata.labels.get('app.kubernetes.io/name') or pod.metadata.labels.get('app')
                
                if app_label:
                    display_name = str(app_label)
                else:
                    # Fallback: Strip deployment hashes or statefulset indexes dynamically
                    parts = pod.metadata.name.split('-')
                    if len(parts) > 2 and len(parts[-1]) == 5: 
                        display_name = '-'.join(parts[:-2])
                    elif len(parts) > 1 and parts[-1].isdigit():
                        display_name = '-'.join(parts[:-1])
                    else:
                        display_name = '-'.join(parts[:-1]) if len(parts) > 1 else pod.metadata.name
                
                # Format to Title Case (e.g., "kube-state-metrics" -> "Kube State Metrics")
                display_name = display_name.replace('-', ' ').title()
                
                # 2. Status mapping
                phase = pod.status.phase
                if phase == "Running":
                    status_label = "SECURE"
                elif phase == "Pending":
                    status_label = "STABILIZING" 
                else:
                    status_label = "ALERT"

                pod_results.append({
                    "name": display_name,         
                    "pod_name": pod.metadata.name, 
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

def get_pod_logs(namespace: str, pod_name: str):
    """
    SRE Feature: Retrieves the last 50 lines of logs for a specific pod.
    Dynamically identifies the primary container to support multi-container pods (Sidecars).
    """
    if not v1:
        return "⚠️ K8s Client not initialized."
    try:
        # 1. Fetch the pod metadata to inspect containers
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        if not pod.spec.containers:
            return "CRITICAL ERROR: No containers found in the targeted pod."
        
        # 2. Extract the name of the first (primary) container
        primary_container = pod.spec.containers[0].name
        
        # 3. Explicitly request logs for the primary container
        logs = v1.read_namespaced_pod_log(
            name=pod_name, 
            namespace=namespace, 
            container=primary_container, 
            tail_lines=50
        )
        return logs
    except Exception as e:
        print(f"❌ Log Retrieval Error: {str(e)}")
        return f"CRITICAL ERROR: Unable to retrieve logs for {pod_name}. See K-Guard backend logs."

def get_cluster_deployments():
    """Retrieves deployments for security auditing."""
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
    paths = ["/", "/app"]
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

def get_node_capacity():
    """SRE Feature: Dynamically retrieves K3s node capacity for precise metrics UI."""
    if not v1:
        return {"cpu_cores": 2, "memory_total_ki": 8388608}
    try:
        nodes = v1.list_node().items
        if nodes:
            allocatable = nodes[0].status.allocatable
            cpu = allocatable.get("cpu", "2")
            mem = allocatable.get("memory", "8388608Ki")
            
            # Format conversion for frontend calculations
            cpu_cores = int(cpu) if not str(cpu).endswith('m') else int(str(cpu).replace('m', '')) / 1000
            mem_ki = int(str(mem).replace('Ki', ''))
            
            return {"cpu_cores": cpu_cores, "memory_total_ki": mem_ki}
    except Exception as e:
        print(f"❌ Node capacity error: {e}")
    
    # Fallback equivalent to a standard Kamatera VPS
    return {"cpu_cores": 2, "memory_total_ki": 8388608}