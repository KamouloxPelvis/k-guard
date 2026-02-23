# k-guard/backend/network_manager.py
from kubernetes import client, config
import logging

class NetworkSentinel:
    def __init__(self):
        # Charge la config K3s (le fichier yaml que ton installeur a vérifié)
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.net_v1 = client.NetworkingV1Api()

    def get_network_map(self):
        """Génère une carte des flux autorisés et actifs"""
        nodes_map = []
        try:
            # On récupère tous les pods du cluster
            pods = self.v1.list_pod_for_all_namespaces(watch=False)
            for pod in pods.items:
                nodes_map.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "ip": pod.status.pod_ip,
                    "status": pod.status.phase,
                    "labels": pod.metadata.labels
                })
            return nodes_map
        except Exception as e:
            logging.error(f"Erreur Sentinel : {e}")
            return []

    def audit_network_policies(self, namespace="k-guard"):
        """Vérifie si des NetworkPolicies protègent le namespace"""
        policies = self.net_v1.list_namespaced_network_policy(namespace)
        if not policies.items:
            return {"status": "CRITICAL", "message": "Aucune NetworkPolicy détectée ! Flux non restreints."}
        return {"status": "SECURE", "count": len(policies.items)}