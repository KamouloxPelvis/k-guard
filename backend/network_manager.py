from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional
from kubernetes import client, config
import os
import subprocess
import requests
import json

router = APIRouter(tags=["Network Sentinel"])

# --- CONFIGURATION DYNAMIQUE ---
# On utilise des variables d'environnement pour éviter le hardcoding
PROTECTED_NAMESPACES = os.getenv("KGUARD_PROTECTED_NS", "k-guard,blog-prod,portfolio-prod").split(",")
ANSIBLE_PATH = os.getenv("KGUARD_ANSIBLE_PATH", "../infra/ansible/harden_network.yml")

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
    
    # Utilisation de la liste dynamique ou du filtre utilisateur
    target_ns = [ns] if ns else PROTECTED_NAMESPACES
    
    nodes = []
    edges = []
    audit_results = {}

    try:
        for namespace in target_ns:
            # Audit dynamique des politiques
            policies = net_v1.list_namespaced_network_policy(namespace)
            audit_results[namespace] = {
                "policy_count": len(policies.items),
                "status": "SECURE" if len(policies.items) > 0 else "VULNERABLE"
            }

            pods = v1.list_namespaced_pod(namespace)
            for pod in pods.items:
                pod_name = pod.metadata.name
                labels = pod.metadata.labels or {}
                
                nodes.append({
                    "id": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip,
                    "labels": labels,
                    "is_hardened": len(policies.items) > 0
                })

                # LOGIQUE DE GRAPHE DYNAMIQUE (Basée sur les labels)
                # Si le pod a le label de ton blog, on cherche son service de scan
                if labels.get("app") == "blog-devopsnotes":
                    # On crée un lien vers n'importe quel pod ayant le label 'clamav' dans le même NS
                    edges.append({
                        "source": pod_name, 
                        "target": "clamav-service", 
                        "label": "Scanner Flux (3310)"
                    })
                
        return {
            "nodes": nodes,
            "edges": edges,
            "audit": audit_results,
            "monitored_namespaces": target_ns
        }
    except Exception as e:
        return {"error": str(e)}

def get_cloudflare_ips():
    """Récupère dynamiquement les CIDR IPv4 de Cloudflare"""
    try:
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        if response.status_code == 200:
            return response.text.strip().split('\n')
    except Exception as e:
        print(f"Erreur récupération IPs Cloudflare : {e}")
    # Fallback minimaliste
    return ["103.21.244.0/22", "173.245.48.0/20"]

@router.post("/sentinel/harden")
async def apply_hardening():
    cf_ips = get_cloudflare_ips()
    extra_vars = json.dumps({"cf_ips": cf_ips})
    
    try:
        # Utilisation du chemin dynamique vers le playbook
        result = subprocess.run(
            ["ansible-playbook", ANSIBLE_PATH, "--extra-vars", extra_vars],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel Hardening Applied"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}