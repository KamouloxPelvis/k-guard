import sqlite3
import json
import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from .auth import verify_token
from database import DB_PATH, update_scan_status
from security_manager import run_trivy_scan
from pydantic import BaseModel
from services.cisco_notifier import CiscoWebexNotifier

router = APIRouter(prefix="/scan", tags=["Security Scan"])

class ScanRequest(BaseModel):
    image: str

# 1. Execution Route (Non-blocking)
@router.post("/scan")
async def launch_security_scan(payload: ScanRequest, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """Triggers a Trivy scan in the background to prevent 502/504 gateway timeouts."""
    
    print(f"🔍 [K-GUARD ENGINE] Received scan request for image: {payload.image}")
    
    if "nginx:1.18" in payload.image:
        print("🚀 [DEMO MODE] Stress test detected: Vulnerability simulation active.")
    
    # Offload heavy scanning process to background tasks
    background_tasks.add_task(run_and_store_scan, payload.image)
    
    return {
        "status": "processing", 
        "message": f"Scan for {payload.image} is currently running..."
    }

# 2. Results Retrieval Route (Polling)
@router.get("/results/{image_name:path}")
async def get_scan_results(image_name: str, user: dict = Depends(verify_token)):
    """Retrieves the latest stored scan report from the database for a specific image."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch the most recent report based on creation timestamp
        cursor.execute(
            "SELECT status, report, created_at FROM security_scans WHERE image = ? ORDER BY created_at DESC LIMIT 1",
            (image_name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"status": "not_found", "message": "No scan results found in database for this image."}

        # Deserialize JSON text from DB into a Python object
        report_data = json.loads(row["report"]) if row["report"] else None

        return {
            "status": row["status"],
            "image": image_name,
            "created_at": row["created_at"],
            "data": report_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database access error: {str(e)}")

# 3. Background Processing Logic
def run_and_store_scan(image: str):
    """Core logic to run Trivy scan, save to DB, and notify via Webex."""
    notifier = CiscoWebexNotifier() 
    try:
        # 1. Execute Trivy scan via security_manager
        report = run_trivy_scan(image) 
        
        # 2. Persist results in SQLite database
        update_scan_status(image, "completed", report) 
        
        # 3. CHATOPS ALERTING: Send summary to Cisco Webex if integration is active
        if report and "summary" in report:
            print(f"🛰️ [K-GUARD] Sending report to Webex for {image}")
            notifier.send_scan_report(image, report["summary"]) 

    except Exception as e:
        print(f"❌ [K-GUARD] Scan/Notify Error: {e}")
        update_scan_status(image, "error", {"error": str(e)}) 

@router.get("/debug-storage")
async def debug_storage(user: dict = Depends(verify_token)):
    """Diagnostic route for Trivy cache persistence on PVC."""
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    try:
        # Check cache directory content
        files = []
        if os.path.exists(cache_path):
            files = os.listdir(cache_path)
            # Verify if the 'db' subdirectory exists (Trivy internal database)
            db_exists = os.path.exists(os.path.join(cache_path, "db"))
        else:
            return {"error": f"The directory {cache_path} does not exist."}

        return {
            "mount_path": cache_path,
            "owner_uid": os.stat(cache_path).st_uid,
            "content": files,
            "trivy_db_initialized": db_exists,
            "message": "If 'db' is present, persistence is operational!"
        }
    except Exception as e:
        return {"error": str(e)}