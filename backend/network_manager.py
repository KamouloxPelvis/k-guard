from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional
from kubernetes import client, config
import os
import subprocess
import requests
import json

router = APIRouter(tags=["Network Sentinel"])

# --- CONFIGURATION DYNAMIQUE ---
# Fallback propre : si la variable d'environnement est absente, on check le namespace 'default'
PROTECTED_NAMESPACES = os.getenv("KGUARD_PROTECTED_NS", "default").split(",")
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
    
    nodes = []
    edges = []
    audit_results = {}

    # 1. DÉCOUVERTE DYNAMIQUE DES NAMESPACES
    try:
        if ns:
            target_ns = [ns]
        else:
            # Tentative de récupération globale (nécessite des droits ClusterRole)
            all_ns = v1.list_namespace(timeout_seconds=5)
            target_ns = [
                n.metadata.name for n in all_ns.items 
                if n.metadata.name not in ["kube-system", "kube-public", "kube-node-lease", "local-path-storage"]
            ]
    except Exception as rbac_error:
        # Si le ServiceAccount de K-Guard est restreint, on utilise le .env
        print(f"⚠️ [SENTINEL] Droits ClusterRole limités, utilisation du fallback env : {rbac_error}")
        target_ns = PROTECTED_NAMESPACES

    # 2. SCAN DES RESSOURCES
    try:
        for namespace in target_ns:
            # Audit des Network Policies
            policies = net_v1.list_namespaced_network_policy(namespace)
            audit_results[namespace] = {
                "policy_count": len(policies.items),
                "status": "SECURE" if len(policies.items) > 0 else "VULNERABLE"
            }

            pods = v1.list_namespaced_pod(namespace)
            
            # Listes temporaires pour la création dynamique des flux
            scanner_pods = []
            standard_apps = []

            for pod in pods.items:
                pod_name = pod.metadata.name
                labels = pod.metadata.labels or {}
                role = labels.get("app", "generic").lower()
                
                nodes.append({
                    "id": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip or "0.0.0.0",
                    "labels": labels,
                    "is_hardened": len(policies.items) > 0
                })

                # Tri intelligent basé sur les labels
                if "clamav" in role or "scanner" in role or "trivy" in role:
                    scanner_pods.append(pod_name)
                elif role != "generic":
                    standard_apps.append(pod_name)

            # 3. GÉNÉRATION DES FLUX DYNAMIQUES (Graphe)
            # Lie automatiquement les apps détectées aux pods de sécurité du namespace
            for app in standard_apps:
                for scanner in scanner_pods:
                    edges.append({
                        "source": app, 
                        "target": scanner, 
                        "label": "Scanner Flux (Dynamic)"
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
        result = subprocess.run(
            ["ansible-playbook", ANSIBLE_PATH, "--extra-vars", extra_vars],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel Hardening Applied"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}