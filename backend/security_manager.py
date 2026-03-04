import subprocess
import json
import shutil
import os
from services.cisco_notifier import CiscoWebexNotifier

def run_trivy_scan(image_name: str):
    """
    Core security audit engine: Runs Trivy SCA (Software Composition Analysis) 
    on a target image and dispatches findings.
    """
    print(f"🔍 [K-GUARD ENGINE] Starting security audit for: {image_name}")
    
    # Check for Trivy binary presence in the environment
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        error_msg = "Critical: 'trivy' binary not found in PATH. Please verify installation."
        print(f"❌ [K-GUARD ENGINE] {error_msg}")
        return {"status": "error", "message": error_msg}

    # Demo mode logic for stress-testing and simulation
    if image_name == "nginx:1.18":
        print("🚀 [DEMO MODE] Vulnerability simulation triggered.")
    
    # Path to Trivy cache, ideally mounted on a Persistent Volume (PVC)
    cache_path = os.getenv("TRIVY_CACHE_DIR", "/data/trivy-cache")
    
    try:
        # Define the scan command (focusing on high-impact vulnerabilities)
        command = [
            trivy_path, "image",
            "--cache-dir", cache_path, 
            "--format", "json", 
            "--severity", "HIGH,CRITICAL",
            image_name
        ]
        
        # Execute the scan with a 6-minute timeout to handle large images
        process = subprocess.run(command, capture_output=True, text=True, timeout=360)
        
        if process.returncode != 0:
            print(f"❌ [K-GUARD ENGINE] Trivy Execution Error: {process.stderr}")
            return {"status": "error", "message": process.stderr}

        # Parsing results
        report = json.loads(process.stdout)
        results = report.get('Results', [])
        
        vulnerabilities = []
        if results:
            for res in results:
                if 'Vulnerabilities' in res:
                    vulnerabilities.extend(res.get('Vulnerabilities', []))
        
        # Counting security findings
        critical_count = len([v for v in vulnerabilities if v['Severity'] == 'CRITICAL'])
        high_count = len([v for v in vulnerabilities if v['Severity'] == 'HIGH'])
        
        summary = {"critical": critical_count, "high": high_count}
        print(f"✅ [K-GUARD ENGINE] Audit complete: {critical_count} Critical, {high_count} High vulnerabilities found.")

        # --- 2. CISCO WEBEX ALERT DISPATCH ---
        try:
            notifier = CiscoWebexNotifier()
            notifier.send_scan_report(image_name, summary)
            print(f"📨 [K-GUARD] Webex alert dispatched for {image_name}")
        except Exception as webex_err:
            # Fail-safe: Do not block scan results if notification fails
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