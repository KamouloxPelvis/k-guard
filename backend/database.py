from kubernetes import client, config
import sqlite3
import json
import os

# Initialisation des variables globales
v1 = None
apps_client = None
custom_client = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kguard.db")

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

def init_db():
    """Initialise la table si elle n'existe pas au démarrage du backend"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # On stocke l'image, le statut et le résultat brut en JSON
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image TEXT NOT NULL,
            status TEXT NOT NULL, -- 'processing', 'completed', 'error'
            report TEXT,          -- Le JSON de Trivy sera ici
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Base de données K-Guard initialisée.")

def update_scan_status(image, status, report=None):
    """Met à jour ou insère un résultat de scan"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    report_json = json.dumps(report) if report else None
    
    # On insère un nouveau scan (on garde l'historique)
    cursor.execute(
        "INSERT INTO security_scans (image, status, report) VALUES (?, ?, ?)",
        (image, status, report_json)
    )
    conn.commit()
    conn.close()

init_db()