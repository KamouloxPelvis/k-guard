import os
import logging
import asyncio
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict, Any
from kubernetes import client, config

router = APIRouter(tags=["Network Sentinel"])

# --- CONFIGURATION ---
# Note: In a production environment, avoid executing ansible-playbook from within a pod.
# Consider using an Ansible Operator or a dedicated CI/CD trigger instead.
ANSIBLE_PATH = "/infra/ansible/playbooks/harden_policies.yml"

def load_k8s_config():
    """Initializes in-cluster Kubernetes configuration."""
    try:
        config.load_incluster_config()
        return True
    except Exception as e:
        logging.error("Failed to load In-Cluster K8s config: %s", str(e))
        return False

@router.get("/sentinel/status")
async def get_network_policy_status():
    """
    Checks if K-Guard Network Policies are currently deployed
    across the entire cluster using managed labels.
    """
    try:
        networking_v1 = client.NetworkingV1Api()
        netpols = networking_v1.list_network_policy_for_all_namespaces()
        
        # Verify if our K-Guard managed policy exists using label selectors
        is_deployed = any(
            policy.metadata.labels and policy.metadata.labels.get("managed-by") == "k-guard-sentinel"
            for policy in netpols.items
        )
        
        return {"deployed": is_deployed}
    except Exception as e:
        logging.error("Error checking cluster-wide policies: %s", str(e))
        return {"deployed": False, "error": str(e)}

async def fetch_namespace_data(namespace: str, v1: client.CoreV1Api, net_v1: client.NetworkingV1Api) -> Dict[str, Any]:
    """
    Fetches pods and network policies for a single namespace concurrently.
    """
    try:
        pods = await asyncio.to_thread(v1.list_namespaced_pod, namespace)
        policies = await asyncio.to_thread(net_v1.list_namespaced_network_policy, namespace)
        
        namespace_nodes = []
        for pod in pods.items:
            labels = pod.metadata.labels or {}
            role = labels.get("app", labels.get("k8s-app", "generic"))
            
            namespace_nodes.append({
                "id": pod.metadata.name,
                "name": pod.metadata.name,
                "namespace": namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip or "0.0.0.0",
                "role": role,
                "is_hardened": len(policies.items) > 0
            })
        return {"nodes": namespace_nodes}
    except Exception as e:
        logging.error("Error fetching data for namespace %s: %s", namespace, e)
        return {"nodes": []}

@router.get("/sentinel/map")
async def get_network_map():
    """
    Generates a dynamic map of network flows using parallelized discovery.
    """
    v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    
    try:
        all_ns = await asyncio.to_thread(v1.list_namespace)
        target_ns = [
            n.metadata.name for n in all_ns.items 
            if not n.metadata.name.startswith(("kube-", "local-path-", "node-lease", "ingress-nginx"))
        ]

        results = await asyncio.gather(*[fetch_namespace_data(ns, v1, net_v1) for ns in target_ns])
        nodes = [node for res in results for node in res["nodes"]]
        
        # Build edges representing flow discovery
        edges = []
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                if node_a["namespace"] == node_b["namespace"]:
                    edges.append({
                        "source": node_a["id"],
                        "target": node_b["id"],
                        "label": "Intra-NS Flow"
                    })
                    
        return {"nodes": nodes, "edges": edges, "namespaces": target_ns}
    except Exception as e:
        logging.error("Critical error in network map discovery: %s", str(e))
        return {"error": "SRE Discovery failed"}