from fastapi import APIRouter, Query
from typing import Optional
from kubernetes import client, config
import os
import subprocess

router = APIRouter(tags=["Network Sentinel"])

# --- DYNAMIC CONFIGURATION ---
# No hardcoded namespaces or labels. Everything is discovered via K8s API.
ANSIBLE_PATH = os.getenv("KGUARD_ANSIBLE_PATH", "/app/infra/ansible/playbooks/harden_policies.yml")
# Set the correct path based on your SRE directory structure
TEST_SCRIPT_PATH = os.getenv("KGUARD_TEST_SCRIPT_PATH", "/app/test/connectivity_test.sh")

def load_k8s_config():
    """Loads K8s configuration with auto-detection."""
    try:
        if os.path.exists("/etc/rancher/k3s/k3s.yaml"):
            config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        else:
            config.load_incluster_config()
    except Exception as e:
        print(f"⚠️ Kubernetes configuration error: {e}")

load_k8s_config()

@router.get("/sentinel/map")
async def get_network_map():
    """
    Generates a dynamic map of network flows using Full Auto-Discovery.
    """
    v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    
    nodes = []
    edges = []
    discovered_ns = []

    try:
        # 1. DISCOVERY: List all namespaces except internal system ones
        all_ns = v1.list_namespace(timeout_seconds=5)
        target_ns = [
            n.metadata.name for n in all_ns.items 
            if not n.metadata.name.startswith(("kube-", "local-path-", "node-lease"))
        ]
        discovered_ns = target_ns

        # 2. SCAN: Inventory pods and policies
        for namespace in target_ns:
            policies = net_v1.list_namespaced_network_policy(namespace)
            pods = v1.list_namespaced_pod(namespace)
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                labels = pod.metadata.labels or {}
                
                # Dynamic Role Detection: use 'app' label or fallback to first available label
                role = labels.get("app", labels.get("k8s-app", next(iter(labels.values()), "generic")))
                
                nodes.append({
                    "id": pod_name,
                    "name": pod_name,
                    "namespace": namespace,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip or "0.0.0.0",
                    "role": role,
                    "labels": labels,
                    "is_hardened": len(policies.items) > 0
                })

        # 3. EDGE GENERATION: Logical mapping based on namespace shared context
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                if node_a["namespace"] == node_b["namespace"]:
                    edges.append({
                        "source": node_a["id"],
                        "target": node_b["id"],
                        "label": "Intra-NS Flow"
                    })
                
        return {
            "nodes": nodes,
            "edges": edges,
            "namespaces": discovered_ns
        }
    except Exception as e:
        return {"error": str(e)}

# --- NEW SRE CONTROL PLANE ROUTES ---

@router.post("/sentinel/activate")
async def activate_hardening():
    """
    Triggers the automated Ansible hardening playbook.
    Enforces Zero-Trust Micro-segmentation across the cluster.
    """
    if not os.path.exists(ANSIBLE_PATH):
        return {"status": "ERROR", "details": f"Playbook not found at {ANSIBLE_PATH}"}
    
    try:
        result = subprocess.run(
            ["ansible-playbook", ANSIBLE_PATH],
            capture_output=True, text=True, check=True
        )
        return {"status": "SUCCESS", "message": "Sentinel Strategy Applied"}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}

@router.post("/sentinel/deactivate")
async def deactivate_hardening():
    """
    Emergency Kill Switch: Deactivates all Network Policies managed by K-Guard.
    Restores the cluster to an Allow-All state for debugging.
    """
    try:
        # Deletes only policies created by K-Guard to avoid breaking core K8s CNI rules
        result = subprocess.run(
            ["kubectl", "delete", "netpol", "-l", "managed-by=k-guard-sentinel", "-A"],
            capture_output=True, text=True, check=True
        )
        return {"status": "SUCCESS", "message": "Network policies deactivated. Cluster is OPEN."}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}

@router.post("/sentinel/test")
async def test_connectivity():
    """
    Executes the SRE Netshoot diagnostic script.
    Captures stdout to display the live audit results in the frontend terminal.
    """
    if not os.path.exists(TEST_SCRIPT_PATH):
        return {"output": f"❌ ERROR: Test script not found at {TEST_SCRIPT_PATH}. Please check the path."}
    
    try:
        # Run the bash script and capture the output
        result = subprocess.run(
            ["bash", TEST_SCRIPT_PATH],
            capture_output=True, text=True, check=True
        )
        return {"output": result.stdout}
    except subprocess.CalledProcessError as e:
        # If the script exits with an error code (e.g., due to 'set -e' and a failed ping), 
        # we still want to return the output so the admin sees the failure logs in the UI.
        return {"output": e.stdout + "\n" + e.stderr}