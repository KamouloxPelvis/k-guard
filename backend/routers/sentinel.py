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
    v1 = client.CoreV1Api()
    
    # 1. DÉCOUVERTE DYNAMIQUE : Si ns est vide, on scanne TOUS les namespaces non-système
    if not ns:
        all_ns = v1.list_namespace()
        target_ns = [n.metadata.name for n in all_ns.items 
                     if n.metadata.name not in ["kube-system", "kube-public", "kube-node-lease"]]
    else:
        target_ns = [ns]

    nodes = []
    edges = []

    for namespace in target_ns:
        pods = v1.list_namespaced_pod(namespace)
        for pod in pods.items:
            pod_name = pod.metadata.name
            pod_ip = pod.status.pod_ip or "Pending"
            labels = pod.metadata.labels or {}
            
            # On enrichit le nœud avec l'IP et le rôle (ex: frontend/backend)
            nodes.append({
                "id": pod_name,
                "name": pod_name,
                "namespace": namespace,
                "ip": pod_ip,
                "role": labels.get("app", "unknown"),
                "status": pod.status.phase
            })

            # 2. LOGIQUE DE FLUX INTELLIGENTE (Exemple inter-pod)
            # Si c'est un frontend, il pointe vers le backend du même namespace
            if "frontend" in pod_name.lower():
                # On cherche le backend dans le même namespace
                edges.append({
                    "source": pod_name,
                    "target": f"backend-service-{namespace}", # On cible le service
                    "label": "API Traffic"
                })

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
