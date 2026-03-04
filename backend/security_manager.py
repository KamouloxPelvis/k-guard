import subprocess
import json
import shutil
import os
# --- 1. IMPORTATION DU NOTIFICATEUR ---
from service.cisco_notifier import CiscoWebexNotifier

def run_trivy_scan(image_name: str):
    print(f"🔍 [K-GUARD ENGINE] Starting security audit for: {image_name}")
    
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        error_msg = "Critical: 'trivy' binary not found in PATH. Please check installation."
        print(f"❌ [K-GUARD ENGINE] {error_msg}")
        return {"status": "error", "message": error_msg}

    if image_name == "nginx:1.18":
        print("🚀 [DEMO MODE] Vulnerability simulation triggered.")
    
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    
    try:
        command = [
            trivy_path, "image",
            "--cache-dir", cache_path, 
            "--format", "json", 
            "--severity", "HIGH,CRITICAL",
            image_name
        ]
        
        process = subprocess.run(command, capture_output=True, text=True, timeout=360)
        
        if process.returncode != 0:
            print(f"❌ [K-GUARD ENGINE] Trivy Execution Error: {process.stderr}")
            return {"status": "error", "message": process.stderr}

        report = json.loads(process.stdout)
        results = report.get('Results', [])
        
        vulnerabilities = []
        if results:
            for res in results:
                if 'Vulnerabilities' in res:
                    vulnerabilities.extend(res.get('Vulnerabilities', []))
        
        critical_count = len([v for v in vulnerabilities if v['Severity'] == 'CRITICAL'])
        high_count = len([v for v in vulnerabilities if v['Severity'] == 'HIGH'])
        
        summary = {"critical": critical_count, "high": high_count}
        print(f"✅ [K-GUARD ENGINE] Audit complete: {critical_count} Critical, {high_count} High vulnerabilities found.")

        # --- 2. ENVOI DE L'ALERTE WEBEX ---
        try:
            notifier = CiscoWebexNotifier()
            notifier.send_scan_report(image_name, summary)
            print(f"📨 [K-GUARD] Webex alert dispatched for {image_name}")
        except Exception as webex_err:
            # On ne bloque pas le retour du scan si Webex échoue (fail-safe)
            print(f"⚠️ [K-GUARD] Webex notification failed: {webex_err}")

        return {
            "status": "success",
            "image": image_name,
            "summary": summary,
            "vulnerabilities": [
                {
                    "id": v['VulnerabilityID'], 
                    "pkg": v['PkgName'], 
                    "severity": v['Severity'],
                    "installed_version": v.get('InstalledVersion'),
                    "fixed_version": v.get('FixedVersion')
                }
                for v in vulnerabilities
            ]
        }
    except Exception as e:
        print(f"💥 [K-GUARD ENGINE] Critical System Error: {str(e)}")
        return {"status": "error", "message": str(e)}