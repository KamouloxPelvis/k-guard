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
    net_v1 = client.NetworkingV1Api()
    target_ns = [ns] if ns else ["k-guard", "blog-prod", "portfolio-prod"]
    
    nodes = []
    edges = []
    audit_results = {}

    try:
        for namespace in target_ns:
            # Audit : On compte les NetworkPolicies actives
            policies = net_v1.list_namespaced_network_policy(namespace)
            audit_results[namespace] = {
                "policy_count": len(policies.items),
                "status": "SECURE" if len(policies.items) > 0 else "VULNERABLE"
            }

            pods = v1.list_namespaced_pod(namespace)
            for pod in pods.items:
                pod_name = pod.metadata.name
                nodes.append({
                    "id": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "is_hardened": len(policies.items) > 0
                })

                # Logique de Graphe : Si c'est le blog, on crée un lien vers ClamAV
                # (Dans une version avancée, on analyserait les sélecteurs des NetPol)
                if "blog-devopsnotes" in pod_name:
                    edges.append({"source": pod_name, "target": "clamav", "label": "Scanner Flux"})
                
        return {
            "nodes": nodes,
            "edges": edges,
            "audit": audit_results
        }
    except Exception as e:
        return {"error": str(e)}

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
