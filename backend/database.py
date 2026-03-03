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
    """Initialise les tables de sécurité et d'intégrations au démarrage"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Table des Scans
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image TEXT NOT NULL,
            status TEXT NOT NULL,
            report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Table des Intégrations (orientée Cisco DevNet)
    # On utilise 'name' comme clé primaire pour l'idempotence
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrations (
            name TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            token TEXT,
            target_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertion par défaut pour Webex
    cursor.execute("INSERT OR IGNORE INTO integrations (name, enabled) VALUES ('webex', 0)")
    
    conn.commit()
    conn.close()
    print("✅ Base de données K-Guard (Scans + Integrations) initialisée.")

# Fonction utilitaire pour récupérer la config Webex lors d'un scan
def get_integration_settings(name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Pour accéder par nom de colonne
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM integrations WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

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