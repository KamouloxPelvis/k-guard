import subprocess
import json
import shutil
import os
import threading
import logging
from backend.services.cisco_notifier import CiscoWebexNotifier

# Configure logging for systematic debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("K-Guard.SecurityManager")

# Global lock to prevent concurrent Trivy database access (avoids database/cache lock errors)
trivy_lock = threading.Lock()

class SecurityEngine:
    """
    K-Guard Security Audit Engine: 
    Encapsulates logic for SCA vulnerability scanning using Trivy.
    """
    def __init__(self, cache_path="/var/tmp/kguard-cache"):
        self.cache_path = cache_path
        self.trivy_path = shutil.which("trivy")
        os.makedirs(self.cache_path, exist_ok=True)
        logger.info(f"📁 [K-GUARD ENGINE] Cache directory initialized at: {self.cache_path}")

    def run_scan(self, image_name: str):
        """
        Executes a robust SCA scan on the target image and returns formatted results.
        """
        if not self.trivy_path:
            logger.error("❌ [K-GUARD ENGINE] Trivy binary not found in PATH.")
            return {"status": "error", "message": "Trivy binary not found"}

        # Sanitize input to prevent injection or argument parsing errors
        image_name = image_name.strip()
        logger.info(f"🔍 [K-GUARD ENGINE] Starting security audit for: {image_name}")

        with trivy_lock:
            try:
                # Command construction to ensure single target execution
                command = [
                    self.trivy_path, "image",
                    "--cache-dir", self.cache_path,
                    "--format", "json",
                    "--severity", "HIGH,CRITICAL",
                    "--quiet",
                    image_name
                ]
                
                # Setup environment variables to enforce cache isolation
                scan_env = os.environ.copy()
                scan_env["TRIVY_CACHE_DIR"] = self.cache_path
                
                # Execute scan with timeout to prevent hung processes
                process = subprocess.run(
                    command, env=scan_env, capture_output=True, text=True, timeout=360
                )
                
                if process.returncode != 0:
                    logger.error(f"❌ [K-GUARD ENGINE] Trivy Execution Error: {process.stderr}")
                    return {"status": "error", "message": process.stderr}

                # Securely parse JSON output
                report = json.loads(process.stdout)
                all_vulnerabilities = []
                
                # Flatten and TRANSFORM vulnerability list into a flat structure for the frontend
                for result in report.get('Results', []):
                    for v in result.get('Vulnerabilities', []):
                        # On capture la version fixe, mais on ajoute aussi le statut
                        fixed_version = v.get("FixedVersion")
                        all_vulnerabilities.append({
                            "id": v.get("VulnerabilityID", "N/A"),
                            "package": v.get("PkgName", "N/A"),
                            # Si FixedVersion est vide, on affiche "None / Unfixed" pour déboguer
                            "fixedVersion": fixed_version if fixed_version else "Unfixed", 
                            "severity": v.get("Severity", "UNKNOWN"),
                            "status": v.get("Status", "unknown") # Ajout du statut pour voir si c'est 'fixed' ou 'will_not_fix'
                        })

                # Generate summary
                summary = {
                    "critical": len([v for v in all_vulnerabilities if v.get('severity') == 'CRITICAL']),
                    "high": len([v for v in all_vulnerabilities if v.get('severity') == 'HIGH'])
                }

                logger.info(f"✅ [K-GUARD ENGINE] Audit complete: {summary['critical']} Critical, {summary['high']} High vulnerabilities found.")

                # Dispatch Cisco Webex Alert
                try:
                    CiscoWebexNotifier().send_scan_report(image_name, summary)
                except Exception as e:
                    logger.warning(f"⚠️ [K-GUARD] Webex notification skipped: {e}")

                # Return standardized response structure for the API
                return {
                    "status": "success",
                    "image": image_name,
                    "summary": summary,
                    "vulnerabilities": all_vulnerabilities
                }

            except json.JSONDecodeError:
                logger.error("💥 [K-GUARD ENGINE] Parsing error: Invalid JSON output from Trivy")
                return {"status": "error", "message": "Invalid JSON output"}
            except Exception as e:
                logger.error(f"💥 [K-GUARD ENGINE] System Error: {str(e)}")
                return {"status": "error", "message": str(e)}

def run_trivy_scan(image_name: str):
    """
    Main entry point for backend scan service.
    """
    engine = SecurityEngine()
    return engine.run_scan(image_name)