from kubernetes import client, config
import sqlite3
import json
import os

# --- CONFIGURATION DES CHEMINS ---
# Ce dossier est monté via le 'subPath: database' sur trivy-cache-pvc
DB_DIR = "/app/backend/data"
DB_PATH = os.path.join(DB_DIR, "kguard.db")

# Initialisation des variables globales pour K8s
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

def init_db():
    """Initialise les tables de sécurité et d'intégrations dans le stockage persistant"""
    # 1. S'assurer que le dossier de destination existe
    if not os.path.exists(DB_DIR):
        print(f"📁 Creating database directory: {DB_DIR}")
        os.makedirs(DB_DIR, exist_ok=True)

    print(f"🗄️ Database Path: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table des Scans (Persistance des rapports d'audit)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image TEXT NOT NULL,
            status TEXT NOT NULL,
            report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table des Intégrations (Cisco Webex, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrations (
            name TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            token TEXT,
            target_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertion par défaut pour Webex si inexistante
    cursor.execute("INSERT OR IGNORE INTO integrations (name, enabled) VALUES ('webex', 0)")
    
    conn.commit()
    conn.close()
    print("✅ Base de données K-Guard initialisée et persistante.")

# --- FONCTIONS UTILITAIRES ---

def get_integration_settings(name):
    """Récupère la config d'intégration pour le Notifier"""
    if not os.path.exists(DB_PATH):
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM integrations WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_scan_status(image, status, report=None):
    """Archive un résultat de scan dans la DB persistante"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    report_json = json.dumps(report) if report else None
    
    cursor.execute(
        "INSERT INTO security_scans (image, status, report) VALUES (?, ?, ?)",
        (image, status, report_json)
    )
    conn.commit()
    conn.close()

# Initialisation au chargement du module
init_k8s()
init_db()