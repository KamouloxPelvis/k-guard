import subprocess
import json
import shutil
import os

def run_trivy_scan(image_name: str):
    # Log de début pour le monitoring SRE
    print(f"🔍 [K-GUARD ENGINE] Starting security audit for: {image_name}")
    
    # 1. VÉRIFICATION DU BINAIRE (Sécurité anti-Errno 2)
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        error_msg = "Critical: 'trivy' binary not found in PATH. Please check installation."
        print(f"❌ [K-GUARD ENGINE] {error_msg}")
        return {"status": "error", "message": error_msg}

    # --- LOGIQUE DE DÉMO / STRESS TEST ---
    if image_name == "nginx:1.18":
        print("🚀 [DEMO MODE] Vulnerability simulation triggered via Shift+Click.")
    
    # Récupération du chemin de cache (priorité à l'env, sinon /data/trivy-cache)
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    
    try:
        # On lance Trivy via subprocess avec le chemin absolu trouvé
        command = [
            trivy_path, "image",
            "--cache-dir", cache_path, 
            "--format", "json", 
            "--severity", "HIGH,CRITICAL",
            image_name
        ]
        
        # Timeout de 180s pour éviter de saturer le CPU du VPS [cite: 2026-02-23]
        process = subprocess.run(command, capture_output=True, text=True, timeout=180)
        
        if process.returncode != 0:
            print(f"❌ [K-GUARD ENGINE] Trivy Execution Error: {process.stderr}")
            return {"status": "error", "message": process.stderr}

        report = json.loads(process.stdout)
        results = report.get('Results', [])
        
        # On s'assure qu'il y a des résultats pour éviter le crash sur []
        vulnerabilities = []
        if results:
            for res in results:
                if 'Vulnerabilities' in res:
                    vulnerabilities.extend(res.get('Vulnerabilities', []))
        
        critical_count = len([v for v in vulnerabilities if v['Severity'] == 'CRITICAL'])
        high_count = len([v for v in vulnerabilities if v['Severity'] == 'HIGH'])
        
        print(f"✅ [K-GUARD ENGINE] Audit complete: {critical_count} Critical, {high_count} High vulnerabilities found.")

        return {
            "status": "success",
            "image": image_name,
            "summary": {
                "critical": critical_count,
                "high": high_count
            },
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