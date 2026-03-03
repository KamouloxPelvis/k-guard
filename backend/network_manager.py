from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional
from kubernetes import client, config
import os
import subprocess
import requests
import json

router = APIRouter(tags=["Network Sentinel"])

# --- CONFIGURATION DÉPORTÉE (Variables d'environnement) ---
# Ces valeurs sont injectées via le ConfigMap ou les Secrets du cluster
PROTECTED_NAMESPACES = os.getenv("KGUARD_PROTECTED_NS", "default").split(",")
ANSIBLE_PATH = os.getenv("KGUARD_ANSIBLE_PATH", "/app/infra/ansible/harden_network.yml")
CLOUDFLARE_IPS_URL = "https://www.cloudflare.com/ips-v4"

def load_k8s_config():
    """Charge la config de manière idempotente (Auto-détection)"""
    try:
        if os.path.exists("/etc/rancher/k3s/k3s.yaml"):
            config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        else:
            config.load_incluster_config()
    except Exception as e:
        print(f"⚠️ Configuration K8s non trouvée : {e}")

load_k8s_config()

@router.get("/sentinel/map")
async def get_network_map(ns: Optional[str] = Query(None)):
    v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    
    nodes = []
    edges = []
    audit_results = {}

    try:
        # 1. DÉCOUVERTE DYNAMIQUE (Évite le hardcoding des namespaces)
        if ns:
            target_ns = [ns]
        else:
            try:
                all_ns = v1.list_namespace(timeout_seconds=5)
                # On ignore les namespaces système standards
                target_ns = [
                    n.metadata.name for n in all_ns.items 
                    if n.metadata.name not in ["kube-system", "kube-public", "kube-node-lease", "local-path-storage"]
                ]
            except Exception:
                target_ns = PROTECTED_NAMESPACES

        # 2. SCAN ET AUDIT
        for namespace in target_ns:
            # Audit de conformité : Vérifie si des NetworkPolicies existent
            policies = net_v1.list_namespaced_network_policy(namespace)
            audit_results[namespace] = {
                "policy_count": len(policies.items),
                "status": "SECURE" if len(policies.items) > 0 else "VULNERABLE"
            }

            pods = v1.list_namespaced_pod(namespace)
            
            # Groupes dynamiques basés sur les rôles (labels)
            security_pods = [] # Scanner, IDS, etc.
            app_pods = []      # Web, API, etc.

            for pod in pods.items:
                pod_name = pod.metadata.name
                labels = pod.metadata.labels or {}
                # On utilise un rôle générique si aucun label 'app' n'est présent
                role = labels.get("app", labels.get("k8s-app", "generic")).lower()
                
                nodes.append({
                    "id": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip or "0.0.0.0",
                    "role": role,
                    "is_hardened": len(policies.items) > 0
                })

                # Logique de flux basée sur les fonctions, pas sur les noms
                if any(x in role for x in ["scanner", "trivy", "security", "guard"]):
                    security_pods.append(pod_name)
                elif role != "generic":
                    app_pods.append(pod_name)

            # 3. GÉNÉRATION DES FLUX (Abstraite)
            # On lie dynamiquement toute application au service de sécurité du namespace
            for app in app_pods:
                for sec in security_pods:
                    edges.append({
                        "source": app, 
                        "target": sec, 
                        "label": "Security Audit Flow"
                    })
                
        return {
            "nodes": nodes,
            "edges": edges,
            "audit": audit_results,
            "monitored_namespaces": target_ns
        }
    except Exception as e:
        return {"error": str(e)}

def get_external_trust_ips():
    """Récupère dynamiquement les IPs de confiance (ex: Cloudflare)"""
    try:
        response = requests.get(CLOUDFLARE_IPS_URL, timeout=10)
        if response.status_code == 200:
            return response.text.strip().split('\n')
    except Exception as e:
        print(f"Erreur external IPs : {e}")
    return ["103.21.244.0/22"] # Fallback sécurisé minimaliste

@router.post("/sentinel/harden")
async def apply_hardening():
    """Applique le hardening de manière idempotente via Ansible"""
    trusted_ips = get_external_trust_ips()
    extra_vars = json.dumps({"trusted_ips": trusted_ips})
    
    if not os.path.exists(ANSIBLE_PATH):
        return {"status": "ERROR", "details": f"Playbook introuvable à {ANSIBLE_PATH}"}
    
    try:
        # Exécution idempotente : Ansible ne modifiera rien si la config est déjà correcte
        result = subprocess.run(
            ["ansible-playbook", ANSIBLE_PATH, "--extra-vars", extra_vars],
            capture_output=True, text=True, check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel Hardening Synced"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}