import os
import subprocess
from pathlib import Path
from fastapi import APIRouter
from kubernetes import client, config

router = APIRouter()

# --- CONFIGURATION ---
# Path defined as absolute to avoid ambiguity regardless of execution context
BASE_DIR = Path("/home/kamal/infrastructure/apps/k-guard")
SCRIPT_PATH = BASE_DIR / "tests" / "check_connectivity.sh"
KUBE_CONFIG = "/etc/rancher/k3s/k3s.yaml"

@router.post("/sentinel/test", tags=["Sentinel"])
async def run_isolation_audit():
    """
    Executes an automated network isolation audit.
    Loads K3s config explicitly to ensure cluster connectivity.
    """
    # 1. Initialize Kubernetes client
    try:
        if os.path.exists(KUBE_CONFIG):
            config.load_kube_config(config_file=KUBE_CONFIG)
        else:
            return {"output": "❌ FATAL: K3s configuration not found at " + KUBE_CONFIG}
    except Exception as e:
        return {"output": f"❌ K8S INIT ERROR: {str(e)}"}

    # 2. Check for diagnostic script
    if not SCRIPT_PATH.exists():
        return {"output": f"❌ SCRIPT ERROR: Diagnostic script missing at {SCRIPT_PATH}"}

    # 3. Execution
    try:
        result = subprocess.run(
            [str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return {"output": f"❌ SCRIPT ERROR: {result.stderr}"}
            
        return {"output": result.stdout}
        
    except Exception as e:
        return {"output": f"❌ EXECUTION ERROR: {str(e)}"}