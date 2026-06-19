import sqlite3
import json
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from .auth import verify_token
from backend.database import DB_PATH, update_scan_status
from backend.security_manager import run_trivy_scan
from backend.services.cisco_notifier import CiscoWebexNotifier

# Standard SRE logging initialization
# Ensuring traceability for background processes in K3s environment
logger = logging.getLogger("kguard.scan")

router = APIRouter(prefix="/scan", tags=["Security Scan"])

class ScanRequest(BaseModel):
    """Data model for incoming security scan requests."""
    image: str

# --- 0. Test internal API connectivity at startup ---
import requests
try:
    response = requests.get("http://localhost:8000/api/health") # Vérifie si l'API répond
    print(f"DEBUG: Internal API check on 8000: {response.status_code}")
except Exception as e:
    print(f"DEBUG: Internal API check FAILED: {e}")

# --- 1. EXECUTION ROUTE (NON-BLOCKING) ---
@router.post("/scan")
async def launch_security_scan(payload: ScanRequest, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    Triggers a Trivy scan in the background to prevent 502/504 gateway timeouts.
    Required for heavy container images that exceed standard HTTP request limits.
    """
    logger.info(f"🔍 [K-GUARD ENGINE] Received scan request for image: {payload.image}")
    
    # Stress test simulation for specific image versions used in DevSecOps demos
    if "nginx:1.18" in payload.image:
        logger.debug("🚀 [DEMO MODE] Stress test detected: Vulnerability simulation active.")
    
    # Offloading heavy scanning process to FastAPI background tasks
    background_tasks.add_task(run_and_store_scan, payload.image)
    
    return {
        "status": "processing", 
        "message": f"Scan for {payload.image} is currently running..."
    }

# --- 2. RESULTS RETRIEVAL ROUTE (POLLING) ---
@router.get("/results/{image_name:path}")
async def get_scan_results(image_name: str, user: dict = Depends(verify_token)):
    """
    Retrieves the latest stored scan report from the database for a specific image.
    Enables the Frontend to poll for updates once the background task is complete.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Selecting latest result to maintain state consistency
        cursor.execute(
            "SELECT status, report, created_at FROM security_scans WHERE image = ? ORDER BY created_at DESC LIMIT 1",
            (image_name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"status": "not_found", "message": "No scan results found in database for this image."}

        # Parsing stored JSON string back to dictionary for API response
        report_data = json.loads(row["report"]) if row["report"] else None

        return {
            "status": row["status"],
            "image": image_name,
            "created_at": row["created_at"],
            "data": report_data
        }
    except Exception as e:
        # SRE Best Practice: Log actual error server-side, hide stack trace from clients
        logger.error(f"❌ [DB ERROR] Failed to retrieve scan results: {e}")
        raise HTTPException(status_code=500, detail="Database access error occurred.")

# --- 3. CORE PROCESSING LOGIC (BACKGROUND WORKER) ---
def run_and_store_scan(image: str):
    """
    Orchestrates the Trivy scanning lifecycle: Execution -> Storage -> Notification.
    This function runs outside the main thread to ensure high availability.
    """
    notifier = CiscoWebexNotifier() 
    try:
        # Step 1: Execute the vulnerability scanner
        logger.info(f"🔍 [SCANNER] Attempting to scan: {image}")
        report = run_trivy_scan(image) 
        
        logger.info(f"DEBUG: Trivy returned report type: {type(report)}")
        logger.debug(f"DEBUG: Full report content: {report}")

        # Step 2: Persist results to the SQLite database
        update_scan_status(image, "completed", report) 
        
        # Step 3: Dynamic structure validation for Webex Notification
        # Supports multiple report formats to prevent silent notification failures
        summary_data = None
        if report and isinstance(report, dict):
            summary_data = report.get("summary") or report.get("vulnerabilities")

        if summary_data:
            logger.info(f"🛰️ [K-GUARD] Compliance condition met. Dispatching Webex alert for: {image}")
            notifier.send_scan_report(image, summary_data)
        else:
            logger.warning(f"⚠️ [K-GUARD] Scan completed for {image} but report structure missing summary keys.")

    except Exception as e:
        # Prevents background task crashes from affecting the main API process
        logger.error(f"❌ [K-GUARD] Critical failure in scan/notification pipeline: {e}")
        update_scan_status(image, "error", {"error": "Execution context interrupted. Check server logs."})

# --- 4. SRE DIAGNOSTIC ENDPOINT ---
@router.get("/debug-storage")
async def debug_storage(user: dict = Depends(verify_token)):
    """
    Diagnostic route for Trivy cache persistence on the K3s Persistent Volume (PV).
    Ensures that vulnerability databases are correctly stored across pod lifecycles.
    """
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    try:
        if not os.path.exists(cache_path):
            return {"error": "Configured cache directory is unreachable."}

        files = os.listdir(cache_path)
        db_exists = os.path.exists(os.path.join(cache_path, "db"))

        return {
            "mount_path": cache_path,
            "owner_uid": os.stat(cache_path).st_uid,
            "content": files,
            "trivy_db_initialized": db_exists,
            "message": "Persistence operational" if db_exists else "Initializing cache database..."
        }
    except Exception as e:
        logger.error(f"❌ [STORAGE DEBUG] Filesystem access error: {e}")
        return {"error": "Internal server error occurred during storage diagnostic."}