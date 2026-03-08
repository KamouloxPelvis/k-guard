    from fastapi import APIRouter, Query
    from typing import Optional
    from kubernetes import client, config
    import os
    import subprocess
    import logging

    router = APIRouter(tags=["Network Sentinel"])

    # --- DYNAMIC CONFIGURATION ---
    # Correcting paths: Using relative roots to match your SRE directory structure.
    ANSIBLE_PATH = os.getenv("KGUARD_ANSIBLE_PATH", "infra/ansible/playbooks/harden_policies.yml")
    TEST_SCRIPT_PATH = os.getenv("KGUARD_TEST_SCRIPT_PATH", "test/check_connectivity.sh")

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
            all_ns = v1.list_namespace(timeout_seconds=5)
            target_ns = [
                n.metadata.name for n in all_ns.items 
                if not n.metadata.name.startswith(("kube-", "local-path-", "node-lease"))
            ]
            discovered_ns = target_ns

            for namespace in target_ns:
                policies = net_v1.list_namespaced_network_policy(namespace)
                pods = v1.list_namespaced_pod(namespace)
                
                for pod in pods.items:
                    pod_name = pod.metadata.name
                    labels = pod.metadata.labels or {}
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
            # Security: Logging full error server-side while returning generic message [cite: 2026-03-07]
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

    @router.post("/sentinel/test")
    async def test_connectivity():
        """Executes the SRE connectivity diagnostic script."""
        if not os.path.exists(TEST_SCRIPT_PATH):
            return {"output": f"❌ ERROR: Test script not found at {TEST_SCRIPT_PATH}"}
        
        try:
            result = subprocess.run(
                ["bash", TEST_SCRIPT_PATH],
                capture_output=True, text=True, check=True
            )
            return {"output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"output": e.stdout + "\n" + e.stderr}