from fastapi import HTTPException
from backend.database import v1, apps_client, custom_client

def parse_cpu(cpu_raw):
    """Converts K8s CPU units (nanocores, microcores, millicores) to millicores (m)."""
    cpu_str = str(cpu_raw)
    try:
        if cpu_str.endswith('n'):
            return int(cpu_str.replace('n', '')) // 1000000
        if cpu_str.endswith('u'): # Handle microcores for lightweight K3s envs
            return int(cpu_str.replace('u', '')) // 1000
        if cpu_str.endswith('m'):
            return int(cpu_str.replace('m', ''))
        return int(float(cpu_str)) # Handles decimal inputs
    except ValueError:
        return 0

def parse_memory(mem_raw):
    """Converts K8s Memory units (Ki, Mi, Gi) to MegaBytes (MiB)."""
    mem_str = str(mem_raw)
    if mem_str.endswith('Ki'):
        return int(mem_str.replace('Ki', '')) // 1024
    if mem_str.endswith('Mi'):
        return int(mem_str.replace('Mi', ''))
    if mem_str.endswith('Gi'):
        return int(mem_str.replace('Gi', '')) * 1024
    # Default fallback for raw bytes
    return int(mem_str) // (1024 * 1024)

def get_pod_metrics(namespace: str = None):
    """Fetches real-time CPU/RAM usage from the Metrics Server API."""
    if not custom_client:
        return []

    try:
        if namespace:
            # Query namespaced custom objects (metrics.k8s.io group)
            metrics = custom_client.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1",
                namespace=namespace, plural="pods"
            )
        else:
            # Cluster-wide metrics query
            metrics = custom_client.list_cluster_custom_object(
                group="metrics.k8s.io", version="v1beta1", plural="pods"
            )
        
        parsed_metrics = []
        for item in metrics.get("items", []):
            # --- METADATA EXTRACTION ---
            pod_metadata = item.get("metadata", {})
            p_name = pod_metadata.get("name")
            p_ns = pod_metadata.get("namespace")
            
            containers = item.get("containers", [])
            if not containers or not p_name:
                continue
            
            total_cpu = 0
            total_mem = 0
            for container in containers:
                usage = container.get("usage", {})
                if usage:
                    total_cpu += parse_cpu(usage.get("cpu", 0))
                    total_mem += parse_memory(usage.get("memory", 0))
            
            parsed_metrics.append({
                "pod_name": p_name,
                "namespace": p_ns,
                "cpuUsage": total_cpu,
                "memoryUsage": total_mem
            })
            
        return parsed_metrics
    except Exception as e:
        print(f"🚨 Metrics-Server Error: {str(e)}") 
        return []

async def scale_down_deployment(namespace: str, pod_name: str):
    """
    SRE Feature: Triggers an automated scaling action to remediate 
    resource pressure or potential security risks identified by Falco/Wazuh.
    """
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        if not pod.metadata.owner_references:
            raise Exception("Pod has no parent owner (standalone pod)")
            
        rs_name = pod.metadata.owner_references[0].name
        # Logic to identify the parent Deployment from the ReplicaSet name
        deployment_name = rs_name.rsplit('-', 1)[0]
        
        # Scaling down to 1 replica (Stabilization/Quarantine mode)
        body = {"spec": {"replicas": 1}}
        apps_client.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=body
        )
        return {"status": "success", "message": f"Remediation: {deployment_name} scaled down to 1 replica."}
    except Exception as e:
        print(f"❌ Scale Down Fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))