from database import v1, apps_client
import shutil
import os

# Namespaces à ignorer
SYSTEM_NS = ["kube-system", "kube-public", "kube-node-lease", "local-path-storage", "cert-manager", "ingress-nginx"]

def get_k3s_status():
    """Récupère l'état de santé des Pods pour le Dashboard"""
    if not v1:
        print("⚠️ K8s Client (v1) non initialisé")
        return []
    
    pod_results = []
    try:
        # On scanne tous les namespaces (autorisé par le clusterRole RBAC)
        pods = v1.list_pod_for_all_namespaces(watch=False)
        for pod in pods.items:
            ns = pod.metadata.namespace
            
            if ns not in SYSTEM_NS:
                # 1. Gestion du nom d'affichage vs nom technique unique
                app_label = pod.metadata.labels.get('app')
                display_name = app_label if app_label else pod.metadata.name.split('-')[0]
                
                # 2. Mapping intelligent des statuts pour éviter les fausses alertes
                phase = pod.status.phase
                if phase == "Running":
                    status_label = "SECURE"
                elif phase == "Pending":
                    status_label = "STABILIZING" # Moins alarmant que ALERT
                else:
                    status_label = "ALERT"

                pod_results.append({
                    "name": display_name,         # Pour l'affichage UI
                    "pod_name": pod.metadata.name, # Identifiant unique pour les logs
                    "namespace": ns,
                    "status": status_label,
                    "ip": pod.status.pod_ip or "N/A",
                    "type": "k3s Pod",
                    "creation": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                })
        return pod_results 
    except Exception as e:
        print(f"❌ Erreur Health Status: {e}")
        return []

def get_cluster_deployments():
    """Récupère les déploiements pour l'audit de sécurité (Trivy)"""
    if not apps_client:
        print("⚠️ K8s AppsClient non initialisé")
        return []
        
    try:
        deps = apps_client.list_deployment_for_all_namespaces()
        app_list = []
        for dep in deps.items:
            ns = dep.metadata.namespace
            if ns not in SYSTEM_NS:
                # On récupère l'image du premier conteneur (standard pour nos apps)
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
    """Vérifie l'espace disque sur les points de montage critiques"""
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
    """Supprime proprement le contenu du cache Trivy sur le PVC"""
    cache_path = "/data/trivy-cache"
    try:
        if os.path.exists(cache_path):
            # On vide le contenu sans supprimer le dossier racine (le point de montage)
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