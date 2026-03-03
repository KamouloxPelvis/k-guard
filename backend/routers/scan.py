import sqlite3
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from .auth import verify_token
from database import DB_PATH, update_scan_status
from security_manager import run_trivy_scan
from pydantic import BaseModel
from services.cisco_notifier import CiscoWebexNotifier

router = APIRouter(prefix="/scan", tags=["Security Scan"])

class ScanRequest(BaseModel):
    image: str

# 1. Route de lancement (Non-bloquante)
@router.post("/scan")
async def launch_security_scan(payload: ScanRequest, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """Lance le scan Trivy en tâche de fond pour éviter les timeouts 502/504."""
    
    print(f"🔍 [K-GUARD ENGINE] Received scan request for image: {payload.image}")
    
    if "nginx:1.18" in payload.image:
        print("🚀 [DEMO MODE] Stress test detected: Vulnerability simulation active.")
    
    background_tasks.add_task(run_and_store_scan, payload.image)
    
    return {
        "status": "processing", 
        "message": f"Scan de {payload.image} en cours d'exécution..."
    }

# 2. Route de récupération des résultats (Polling)
@router.get("/results/{image_name:path}")
async def get_scan_results(image_name: str, user: dict = Depends(verify_token)):
    """Récupère le dernier rapport stocké en base pour une image spécifique."""
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
            return {"status": "not_found", "message": "Aucun scan en base pour cette image."}

        # Conversion du texte JSON de la DB en objet Python
        report_data = json.loads(row["report"]) if row["report"] else None

        return {
            "status": row["status"],
            "image": image_name,
            "created_at": row["created_at"],
            "data": report_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'accès DB: {str(e)}")

# 3. Fonction de traitement en arrière-plan
def run_and_store_scan(image: str):
    notifier = CiscoWebexNotifier() # Instanciation
    try:
        # 1. Exécution du scan Trivy via security_manager
        report = run_trivy_scan(image) #
        
        # 2. Sauvegarde en base SQLite via database.py
        update_scan_status(image, "completed", report) #
        
        # 3. ALERTE CHATOPS : Envoi du rapport sur Webex si activé
        if report and "summary" in report:
            print(f"🛰️ [K-GUARD] Sending report to Webex for {image}")
            notifier.send_scan_report(image, report["summary"]) #

    except Exception as e:
        print(f"❌ [K-GUARD] Scan/Notify Error: {e}")
        update_scan_status(image, "error", {"error": str(e)}) #

@router.get("/debug-storage")
async def debug_storage(user: dict = Depends(verify_token)):
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    try:
        # On liste le contenu du dossier de cache
        files = []
        if os.path.exists(cache_path):
            files = os.listdir(cache_path)
            # On vérifie si le sous-dossier 'db' existe (créé par Trivy)
            db_exists = os.path.exists(os.path.join(cache_path, "db"))
        else:
            return {"error": f"Le dossier {cache_path} n'existe pas."}

        return {
            "mount_path": cache_path,
            "owner_uid": os.stat(cache_path).st_uid,
            "content": files,
            "trivy_db_initialized": db_exists,
            "message": "Si 'db' est présent, la persistance est opérationnelle !"
        }
    except Exception as e:
        return {"error": str(e)}
