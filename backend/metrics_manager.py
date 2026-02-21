from fastapi import HTTPException
from database import v1, apps_client, custom_client # <--- On importe custom_client

def parse_cpu(cpu_raw):
    cpu_str = str(cpu_raw)
    try:
        if cpu_str.endswith('n'):
            return int(cpu_str.replace('n', '')) // 1000000
        if cpu_str.endswith('u'): # Ajout des microcores, fréquents en K3s
            return int(cpu_str.replace('u', '')) // 1000
        if cpu_str.endswith('m'):
            return int(cpu_str.replace('m', ''))
        return int(float(cpu_str)) # Gère les nombres à virgule
    except:
        return 0

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

def get_pod_metrics(namespace: str = None): # On passe à None par défaut
    if not custom_client:
        return []

    try:
        # Si namespace est None, on récupère TOUT le cluster (plus utile pour un Dashboard)
        if namespace:
            metrics = custom_client.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1",
                namespace=namespace, plural="pods"
            )
        else:
            metrics = custom_client.list_cluster_custom_object(
                group="metrics.k8s.io", version="v1beta1", plural="pods"
            )
        
        parsed_metrics = []
        for item in metrics.get("items", []):
            containers = item.get("containers", [])
            if not containers:
                continue
            
            # On prend le premier conteneur, mais avec sécurité
            usage = containers[0].get("usage", {})
            if not usage:
                continue

            # Somme des métriques de tous les conteneurs du pod
            total_cpu = 0
            total_mem = 0
            for container in item["containers"]:
                usage = container["usage"]
                total_cpu += parse_cpu(usage["cpu"])
                total_mem += parse_memory(usage["memory"])
            
            parsed_metrics.append({
                "pod_name": name,
                "namespace": ns, # Ajout du NS pour le Front
                "cpuUsage": total_cpu,
                "memoryUsage": total_mem
            })
        print(f"DEBUG: Found {len(parsed_metrics)} pods with metrics")
        return parsed_metrics
    except Exception as e:
        print(f"ℹ️ Metrics-Server indisponible ou erreur: {str(e)}") 
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