import os
from kubernetes import client, config
from pathlib import Path
from dotenv import load_dotenv
import sqlite3

# --- PATH CONFIGURATION ---
APP_ROOT = Path("/app").resolve()
base_dir = Path(__file__).resolve().parent
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

DB_DIR = os.getenv("DB_DIR", str(APP_ROOT / "data"))
DB_PATH = os.path.join(DB_DIR, "kguard.db")

# Global variables initialization for K8s clients
v1 = None
apps_client = None
custom_client = None

def init_k8s():
    """Initializes Kubernetes API clients (Local or In-Cluster context)."""
    global v1, apps_client, custom_client
    if v1 is not None:
        return

    try:
        # Attempt to load configuration (Local Kubeconfig or In-Cluster Service Account)
        try:
            config.load_kube_config()
        except Exception:
            config.load_incluster_config()
        
        v1 = client.CoreV1Api()
        apps_client = client.AppsV1Api()
        custom_client = client.CustomObjectsApi()
    except Exception as e: 
        print(f"❌ Critical: Failed to load K8s config: {e}")

def init_db():
    """Initializes integration and security event tables in persistent storage."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Integrations table for external services (Webex, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrations (
            name TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            token TEXT,
            target_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Security events table to persist alerts from Falco/Wazuh
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            severity TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO integrations (name, enabled) VALUES ('webex', 0)")
    
    conn.commit()
    conn.close()

def get_integration_settings(name):
    """Retrieves integration configuration for the Notifier service."""
    if not os.path.exists(DB_PATH):
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM integrations WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Automatic initialization on module load
init_k8s()
init_db()