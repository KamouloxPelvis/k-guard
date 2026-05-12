import os
from kubernetes import client, config
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import json

# --- PATH CONFIGURATION ---
base_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=base_dir / ".env")

DB_DIR = os.getenv("DB_DIR", os.path.join(base_dir, "data"))
DB_PATH = os.path.join(DB_DIR, "kguard.db")

# Global variables initialization for K8s clients
v1 = None
apps_client = None
custom_client = None

def init_k8s():
    """Initializes Kubernetes API clients (Local or In-Cluster context)"""
    global v1, apps_client, custom_client
    if v1 is not None:
        return

    try:
        # Attempt to load configuration (Local Kubeconfig or In-Cluster Service Account)
        try:
            config.load_kube_config()
            print("✅ K3s Config: Local Kubeconfig loaded")
        except Exception:
            config.load_incluster_config()
            print("✅ K3s Config: In-Cluster Service Account loaded")

        # API Clients initialization
        v1 = client.CoreV1Api()
        apps_client = client.AppsV1Api()
        custom_client = client.CustomObjectsApi()
        
    except Exception as e: 
        print(f"❌ Critical: Failed to load K8s config: {e}")
        v1 = None
        apps_client = None
        custom_client = None

def init_db():
    """Initializes security and integration tables in persistent storage"""
    # 1. Ensure the destination directory exists (for PVC mounting)
    if not os.path.exists(DB_DIR):
        print(f"📁 Creating database directory: {DB_DIR}")
        os.makedirs(DB_DIR, exist_ok=True)

    print(f"🗄️ Database Path: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Scans Table (Persisting audit reports for historical analysis)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image TEXT NOT NULL,
            status TEXT NOT NULL,
            report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Integrations Table (Cisco Webex, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrations (
            name TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            token TEXT,
            target_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default Webex record if it doesn't exist
    cursor.execute("INSERT OR IGNORE INTO integrations (name, enabled) VALUES ('webex', 0)")
    
    conn.commit()
    conn.close()
    print("✅ K-Guard database initialized and persistent.")

# --- UTILITY FUNCTIONS ---

def get_integration_settings(name):
    """Retrieves integration configuration for the Notifier service"""
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
    """Archives a scan result into the persistent database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    report_json = json.dumps(report) if report else None
    
    cursor.execute(
        "INSERT INTO security_scans (image, status, report) VALUES (?, ?, ?)",
        (image, status, report_json)
    )
    conn.commit()
    conn.close()

# Automatic initialization on module load
init_k8s()
init_db()