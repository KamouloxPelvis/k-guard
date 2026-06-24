import logging
from backend.services.cisco_notifier import CiscoWebexNotifier

# Configure logging for systematic debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("K-Guard.SecurityManager")

class SecurityEngine:
    """
    K-Guard Security Engine: 
    Unified gateway for security alerts (Falco, Wazuh, and System events).
    """
    def __init__(self):
        logger.info("🛡️ [K-GUARD ENGINE] Security Engine initialized for Falco/Wazuh integration.")

    def dispatch_alert(self, source: str, event_data: dict):
        """
        Receives an alert from Falco or Wazuh and processes it for notification.
        """
        logger.info(f"🚨 [K-GUARD ENGINE] Alert received from {source}")
        
        # Prepare alert summary for the notification service
        summary = {
            "source": source,
            "severity": event_data.get("priority", "INFO"),
            "message": event_data.get("message", "No description provided")
        }

        # Dispatch Cisco Webex Alert via the notification service
        try:
            CiscoWebexNotifier().send_scan_report(f"Alert from {source}", summary)
        except Exception as e:
            logger.warning(f"⚠️ [K-GUARD] Webex notification failed: {e}")

        return {"status": "success", "alert_processed": True}

def process_security_event(source: str, event_data: dict):
    """
    Primary entry point for security webhooks (e.g., Falco/Wazuh).
    """
    engine = SecurityEngine()
    return engine.dispatch_alert(source, event_data)