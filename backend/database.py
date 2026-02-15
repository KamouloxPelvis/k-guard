from kubernetes import client, config
import os

# Initialisation des variables globales
v1 = None
apps_client = None
custom_client = None

def init_k8s():
    global v1, apps_client, custom_client
    
    if v1 is not None:
        return

    try:
        # Tente de charger la config (Locale ou In-Cluster)
        try:
            config.load_kube_config()
            print("✅ K3s Config: Local Kubeconfig loaded")
        except Exception:
            config.load_incluster_config()
            print("✅ K3s Config: In-Cluster Service Account loaded")

        # Initialisation des clients API
        v1 = client.CoreV1Api()
        apps_client = client.AppsV1Api()
        custom_client = client.CustomObjectsApi()
        
    except Exception as e:
        print(f"❌ Critical: Failed to load K8s config: {e}")
        v1 = None
        apps_client = None
        custom_client = None

init_k8s()