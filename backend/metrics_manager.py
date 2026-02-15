from fastapi import HTTPException
from database import v1, apps_client, custom_client # <--- On importe custom_client

def parse_cpu(cpu_raw):
    """Convertit les nanocores (n) ou millicores (m) en millicores (entier)"""
    cpu_str = str(cpu_raw) # Sécurité si c'est déjà un int
    if cpu_str.endswith('n'):
        return int(cpu_str.replace('n', '')) // 1000000
    if cpu_str.endswith('m'):
        return int(cpu_str.replace('m', ''))
    return int(cpu_str)

def parse_memory(mem_raw):
    """Convertit Ki, Mi, Gi en MegaBytes (MiB)"""
    mem_str = str(mem_raw)
    if mem_str.endswith('Ki'):
        return int(mem_str.replace('Ki', '')) // 1024
    if mem_str.endswith('Mi'):
        return int(mem_str.replace('Mi', ''))
    if mem_str.endswith('Gi'):
        return int(mem_str.replace('Gi', '')) * 1024
    # Si c'est juste des bytes
    return int(mem_str) // (1024 * 1024)

def get_pod_metrics(namespace: str = "default"):
    """Récupère les métriques CPU/RAM via metrics.k8s.io"""
    if not custom_client:
        print("⚠️ K8s Custom Client non initialisé")
        return []

    try:
        metrics = custom_client.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
        
        parsed_metrics = []
        for item in metrics.get("items", []):
            name = item["metadata"]["name"]
            # Protection si le pod n'a pas encore de métriques
            if not item.get("containers"):
                continue

            usage = item["containers"][0]["usage"]
            
            parsed_metrics.append({
                "pod_name": name,
                "cpuUsage": parse_cpu(usage["cpu"]),
                "memoryUsage": parse_memory(usage["memory"])
            })
        return parsed_metrics
    except Exception as e:
        # On ne crash pas l'app si metrics-server n'est pas là
        print(f"ℹ️ Info Metrics: {str(e)}") 
        return []

async def scale_down_deployment(namespace: str, pod_name: str):
    # ... (Le reste de ta fonction scale_down était correct)
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        if not pod.metadata.owner_references:
            raise Exception("Pod sans parent")
            
        rs_name = pod.metadata.owner_references[0].name
        # Logique robuste pour trouver le deployment depuis le ReplicaSet
        deployment_name = rs_name.rsplit('-', 1)[0]
        
        body = {"spec": {"replicas": 1}}
        apps_client.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=body
        )
        return {"status": "success", "message": f"Remédiation : {deployment_name} réduit à 1 replica."}
    except Exception as e:
        print(f"❌ Scale Down Fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))