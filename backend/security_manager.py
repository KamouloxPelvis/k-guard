import subprocess
import json

def run_trivy_scan(image_name: str):
    # Log de début pour le monitoring SRE
    print(f"🔍 [K-GUARD ENGINE] Starting security audit for: {image_name}")
    
    # --- LOGIQUE DE DÉMO / STRESS TEST ---
    if image_name == "nginx:1.18":
        print("🚀 [DEMO MODE] Vulnerability simulation triggered via Shift+Click.")
    
    try:
        # On lance Trivy via subprocess
        command = [
            "trivy", "image", 
            "--format", "json", 
            "--severity", "HIGH,CRITICAL",
            image_name
        ]
        
        # Timeout de 180s pour éviter de saturer le CPU du VPS indéfiniment
        process = subprocess.run(command, capture_output=True, text=True, timeout=180)
        
        if process.returncode != 0:
            print(f"❌ [K-GUARD ENGINE] Trivy Error: {process.stderr}")
            return {"status": "error", "message": process.stderr}

        report = json.loads(process.stdout)
        results = report.get('Results', [])
        vulnerabilities = results[0].get('Vulnerabilities', []) if results else []
        
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
                    "fixed_version": v.get('FixedVersion') # Crucial pour le Smart-Patch
                }
                for v in vulnerabilities
            ]
        }
    except Exception as e:
        print(f"💥 [K-GUARD ENGINE] Critical System Error: {str(e)}")
        return {"status": "error", "message": str(e)}