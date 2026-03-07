from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional
from kubernetes import client, config
import os
import subprocess
import requests
import json

router = APIRouter(tags=["Network Sentinel"])

# --- EXTERNALIZED CONFIGURATION (Environment Variables) ---
# These values are injected via Cluster ConfigMaps or Secrets
PROTECTED_NAMESPACES = os.getenv("KGUARD_PROTECTED_NS", "default").split(",")
ANSIBLE_PATH = os.getenv("KGUARD_ANSIBLE_PATH", "/app/infra/ansible/harden_network.yml")
CLOUDFLARE_IPS_URL = "https://www.cloudflare.com/ips-v4"

def load_k8s_config():
    """Loads K8s configuration with idempotency (Auto-detection)"""
    try:
        # Check for local K3s config first, fallback to In-Cluster Service Account
        if os.path.exists("/etc/rancher/k3s/k3s.yaml"):
            config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        else:
            config.load_incluster_config()
    except Exception as e:
        print(f"⚠️ Kubernetes configuration not found: {e}")

load_k8s_config()

@router.get("/sentinel/map")
async def get_network_map(ns: Optional[str] = Query(None)):
    """
    Generates a dynamic map of network flows and security posture per namespace.
    """
    v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    
    nodes = []
    edges = []
    audit_results = {}

    try:
        # 1. DYNAMIC DISCOVERY (Avoids namespace hardcoding)
        if ns:
            target_ns = [ns]
        else:
            try:
                all_ns = v1.list_namespace(timeout_seconds=5)
                # Filter out standard system namespaces to focus on user workloads
                target_ns = [
                    n.metadata.name for n in all_ns.items 
                    if n.metadata.name not in ["kube-system", "kube-public", "kube-node-lease", "local-path-storage"]
                ]
            except Exception:
                # Fallback to predefined protected namespaces if discovery fails
                target_ns = PROTECTED_NAMESPACES

        # 2. SCAN AND AUDIT
        for namespace in target_ns:
            # Compliance Audit: Verify existing NetworkPolicies
            policies = net_v1.list_namespaced_network_policy(namespace)
            audit_results[namespace] = {
                "policy_count": len(policies.items),
                "status": "SECURE" if len(policies.items) > 0 else "VULNERABLE"
            }

            pods = v1.list_namespaced_pod(namespace)
            
            # Dynamic grouping based on roles/labels
            security_pods = [] # Scanners, IDS, etc.
            app_pods = []      # Web, API, etc.

            for pod in pods.items:
                pod_name = pod.metadata.name
                labels = pod.metadata.labels or {}
                # Use generic role if 'app' or 'k8s-app' labels are missing
                role = labels.get("app", labels.get("k8s-app", "generic")).lower()
                
                nodes.append({
                    "id": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip or "0.0.0.0",
                    "role": role,
                    "labels": labels,  # On ajoute l'objet complet ici !
                    "is_hardened": len(policies.items) > 0
                })

                # Functional flow logic (independent of naming conventions)
                if any(x in role for x in ["scanner", "trivy", "security", "guard"]):
                    security_pods.append(pod_name)
                elif role != "generic":
                    app_pods.append(pod_name)

            # 3. FLOW GENERATION (Abstracted)
            # Dynamically link applications to the namespace security services
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
    """Dynamically fetches trusted external IPs (e.g., Cloudflare)"""
    try:
        response = requests.get(CLOUDFLARE_IPS_URL, timeout=10)
        if response.status_code == 200:
            return response.text.strip().split('\n')
    except Exception as e:
        print(f"Error fetching external IPs: {e}")
    return ["103.21.244.0/22"] # Minimalist secure fallback

@router.post("/sentinel/harden")
async def apply_hardening():
    """Triggers an idempotent network hardening process via Ansible"""
    trusted_ips = get_external_trust_ips()
    extra_vars = json.dumps({"trusted_ips": trusted_ips})
    
    if not os.path.exists(ANSIBLE_PATH):
        return {"status": "ERROR", "details": f"Playbook not found at {ANSIBLE_PATH}"}
    
    try:
        # Idempotent execution: Ansible only modifies configuration if drift is detected
        result = subprocess.run(
            ["ansible-playbook", ANSIBLE_PATH, "--extra-vars", extra_vars],
            capture_output=True, text=True, check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel Hardening Synced"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}