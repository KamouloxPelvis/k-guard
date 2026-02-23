from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional
from kubernetes import client, config
import os
import subprocess
import requests

router = APIRouter(tags=["Network Sentinel"])

# On tente de charger la config K3s (interne au cluster ou externe)
try:
    if os.path.exists("/etc/rancher/k3s/k3s.yaml"):
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    else:
        config.load_incluster_config()
except Exception:
    pass

@router.get("/sentinel/map")
async def get_network_map(ns: Optional[str] = Query(None)):
    """Découvre dynamiquement les pods, leurs IPs et leurs flux de trafic."""
    v1 = client.CoreV1Api()
    nodes = []
    edges = []

    try:
        # 1. Gestion des Namespaces (Dynamique ou Fallback)
        env_ns = os.getenv("KGUARD_PROTECTED_NS", "k-guard,blog-prod,portfolio-prod").split(",")
        
        if not ns:
            try:
                # Tentative de découverte globale (nécessite ClusterRole)
                all_namespaces = v1.list_namespace(timeout_seconds=5)
                target_ns = [n.metadata.name for n in all_namespaces.items 
                             if n.metadata.name not in ["kube-system", "kube-public", "kube-node-lease"]]
            except Exception:
                # Fallback si les droits sont restreints
                target_ns = env_ns
        else:
            target_ns = [ns]

        # 2. Scan des Pods et extraction des métadonnées
        for namespace in target_ns:
            try:
                pods = v1.list_namespaced_pod(namespace, timeout_seconds=5)
                for pod in pods.items:
                    pod_name = pod.metadata.name
                    pod_ip = pod.status.pod_ip or "0.0.0.0" # Sécurité anti-null
                    pod_status = pod.status.phase
                    labels = pod.metadata.labels or {}
                    
                    # On ajoute le nœud avec toutes les infos pour le Frontend
                    nodes.append({
                        "id": pod_name,
                        "name": pod_name,
                        "namespace": namespace,
                        "ip": pod_ip,
                        "status": pod_status,
                        "labels": labels, # Crucial pour afficher le rôle
                        "role": labels.get("app", "generic")
                    })

                    # 3. Logique de Flux (Inter-pod)
                    # Exemple : Lien automatique entre frontend et backend dans le même NS
                    if "frontend" in pod_name.lower():
                        edges.append({
                            "source": pod_name,
                            "target": f"backend-{namespace}", # Cible logique
                            "label": "API Traffic"
                        })
                    
                    # Ton flux spécifique Blog -> ClamAV
                    if "blog-devopsnotes" in pod_name:
                        edges.append({
                            "source": pod_name,
                            "target": "clamav",
                            "label": "Scanner Flux"
                        })

            except Exception as ns_error:
                print(f"⚠️ [SENTINEL] Error scanning namespace {namespace}: {ns_error}")
                continue

        # Réponse propre pour Vue.js (évite 'reading nodes of null')
        return {"nodes": nodes, "edges": edges}

    except Exception as global_error:
        print(f"💥 [SENTINEL] Global failure: {global_error}")
        return {"nodes": [], "edges": [], "error": str(global_error)}

def get_cloudflare_ips():
    """Récupère dynamiquement les CIDR IPv4 de Cloudflare"""
    try:
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        if response.status_code == 200:
            # On transforme le texte brut en liste de lignes
            return response.text.strip().split('\n')
    except Exception as e:
        print(f"Erreur récupération IPs Cloudflare : {e}")
    # Fallback sur une liste de secours si l'API est injoignable
    return ["103.21.244.0/22", "173.245.48.0/20"]

@router.post("/sentinel/harden")
async def apply_hardening():
    # 1. Récupération des IPs fraîches
    cf_ips = get_cloudflare_ips()
    
    # 2. Préparation des variables pour Ansible (Extra Vars)
    # On passe la liste Python sous forme de chaîne JSON pour Ansible
    import json
    extra_vars = json.dumps({"cf_ips": cf_ips})
    
    try:
        result = subprocess.run(
            ["ansible-playbook", "../infra/ansible/harden_network.yml", "--extra-vars", extra_vars],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel a mis à jour les IPs Cloudflare"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}
