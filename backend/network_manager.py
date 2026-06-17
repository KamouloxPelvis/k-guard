import os
import subprocess
import logging
import asyncio
from fastapi import APIRouter, Query
from typing import Optional
from kubernetes import client, config
from typing import List, Dict, Any

print(f"DEBUG: LOADING NETWORK_MANAGER FROM: {__file__}")

router = APIRouter(tags=["Network Sentinel"])

# --- DYNAMIC CONFIGURATION ---
# Correcting paths: Using relative roots to match your SRE directory structure.
ANSIBLE_PATH = "/infra/ansible/playbooks/harden_policies.yml"

def load_k8s_config():
    try:
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        return True
    except AttributeError:
        if hasattr(config, 'load_kubeconfig'):
            config.load_kubeconfig(config_file="/etc/rancher/k3s/k3s.yaml")
        return True
    except Exception as e:
        print(f"Erreur fatale de config: {e}")
        return False

load_k8s_config()

@router.get("/sentinel/status")
async def get_network_policy_status():
    """
    Checks if the K-Guard Network Policies are currently deployed
    across the entire cluster.
    """
    try:
        # Initialize the Networking V1 API client
        networking_v1 = client.NetworkingV1Api()
        
        # Retrieve all network policies across all namespaces in the cluster
        # Using list_network_policy_for_all_namespaces() 
        netpols = networking_v1.list_network_policy_for_all_namespaces()
        
        # Verify if our K-Guard managed policy exists anywhere in the cluster
        # We look for the label 'managed-by=k-guard-sentinel' 
        # This is more robust than checking by name alone.
        is_deployed = any(
            policy.metadata.labels and policy.metadata.labels.get("managed-by") == "k-guard-sentinel"
            for policy in netpols.items
        )
        
        return {"deployed": is_deployed}
        
    except Exception as e:
        logging.exception("Error checking cluster-wide policies")
        return {"deployed": False, "error": str(e)}

async def fetch_namespace_data(namespace: str, v1: client.CoreV1Api, net_v1: client.NetworkingV1Api) -> Dict[str, Any]:
    """
    Fetches pods and network policies for a single namespace concurrently.
    """
    try:
        # We run these two K8s calls in parallel for the specific namespace
        pods_task = asyncio.to_thread(v1.list_namespaced_pod, namespace)
        policies_task = asyncio.to_thread(net_v1.list_namespaced_network_policy, namespace)
        
        pods, policies = await asyncio.gather(pods_task, policies_task)
        
        namespace_nodes = []
        for pod in pods.items:
            labels = pod.metadata.labels or {}
            role = labels.get("app", labels.get("k8s-app", next(iter(labels.values()), "generic")))
            
            namespace_nodes.append({
                "id": pod.metadata.name,
                "name": pod.metadata.name,
                "namespace": namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip or "0.0.0.0",
                "role": role,
                "labels": labels,
                "is_hardened": len(policies.items) > 0
            })
        return {"nodes": namespace_nodes}
    except Exception as e:
        logging.error(f"Error fetching data for namespace {namespace}: {e}")
        return {"nodes": []}

@router.get("/sentinel/map")
async def get_network_map():
    """
    Generates a dynamic map of network flows using parallelized discovery.
    """
    v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    
    try:
        # Fetch namespaces list
        all_ns = await asyncio.to_thread(v1.list_namespace, timeout_seconds=5)
        target_ns = [
            n.metadata.name for n in all_ns.items 
            if not n.metadata.name.startswith(("kube-", "local-path-", "node-lease"))
        ]

        # Parallel fetching for all target namespaces
        results = await asyncio.gather(*[fetch_namespace_data(ns, v1, net_v1) for ns in target_ns])
        
        # Flatten results
        nodes = [node for res in results for node in res["nodes"]]
        
        # Build Edges (Intra-NS flow logic)
        edges = []
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
            "namespaces": target_ns
        }
    except Exception as e:
        logging.exception("Error generating network map")
        return {"error": "Internal SRE Discovery failure"}

@router.post("/sentinel/activate")
async def activate_hardening():
    """Triggers the automated Ansible hardening playbook."""
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
    """Emergency Kill Switch: Removes K-Guard managed Network Policies."""
    try:
        # Using label selector to only remove policies managed by K-Guard
        result = subprocess.run(
            ["kubectl", "delete", "netpol", "-l", "managed-by=k-guard-sentinel", "-A"],
            capture_output=True, text=True, check=True
        )
        return {"status": "SUCCESS", "message": "Network policies deactivated."}
    except subprocess.CalledProcessError as e:
        return {"status": "ERROR", "details": e.stderr}
