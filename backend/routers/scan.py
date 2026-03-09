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
        
        cursor.execute(
            "SELECT status, report, created_at FROM security_scans WHERE image = ? ORDER BY created_at DESC LIMIT 1",
            (image_name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"status": "not_found", "message": "No scan results found in database for this image."}

        report_data = json.loads(row["report"]) if row["report"] else None

        return {
            "status": row["status"],
            "image": image_name,
            "created_at": row["created_at"],
            "data": report_data
        }
    except Exception as e:
        # SRE Security: Log actual error server-side, do not expose stack trace to client
        print(f"❌ [DB ERROR] Failed to retrieve scan results: {e}")
        raise HTTPException(status_code=500, detail="Database access error occurred.")

# 3. Background Processing Logic
def run_and_store_scan(image: str):
    """Core logic to run Trivy scan, save to DB, and notify via Webex."""
    notifier = CiscoWebexNotifier() 
    try:
        report = run_trivy_scan(image) 
        update_scan_status(image, "completed", report) 
        
        if report and "summary" in report:
            print(f"🛰️ [K-GUARD] Sending report to Webex for {image}")
            notifier.send_scan_report(image, report["summary"]) 

    except Exception as e:
        print(f"❌ [K-GUARD] Scan/Notify Error: {e}")
        # Note: We store generic error status in DB to prevent leaking execution contexts
        update_scan_status(image, "error", {"error": "Scan execution failed. Check server logs."}) 

@router.get("/debug-storage")
async def debug_storage(user: dict = Depends(verify_token)):
    """Diagnostic route for Trivy cache persistence on PVC."""
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    try:
        files = []
        if os.path.exists(cache_path):
            files = os.listdir(cache_path)
            db_exists = os.path.exists(os.path.join(cache_path, "db"))
        else:
            return {"error": "Configured cache directory does not exist."}

        return {
            "mount_path": cache_path,
            "owner_uid": os.stat(cache_path).st_uid,
            "content": files,
            "trivy_db_initialized": db_exists,
            "message": "If 'db' is present, persistence is operational!"
        }
    except Exception as e:
        # SRE Security: Prevent filesystem structure leakage
        print(f"❌ [STORAGE DEBUG] Filesystem access error: {e}")
        return {"error": "Internal server error occurred while diagnosing storage."}