import requests
import os

class CiscoWebexNotifier:
    def __init__(self):
        """
        Initializes the Webex Notifier with environment-based configuration.
        Expected variables: WEBEX_BOT_TOKEN, WEBEX_ROOM_ID, WEBEX_ENABLED.
        """
        self.token = os.getenv("WEBEX_BOT_TOKEN")
        self.room_id = os.getenv("WEBEX_ROOM_ID")
        self.enabled = os.getenv("WEBEX_ENABLED", "false").lower() == "true"
        self.api_url = "https://webexapis.com/v1/messages"

    def send_scan_report(self, image, summary):
        """
        Sends a formatted security scan report to the configured Cisco Webex room.
        """
        if not self.enabled or not self.token:
            return
        
        # Select status emoji based on vulnerability severity
        status_emoji = "🚨" if summary['critical'] > 0 else "✅"
        
        # Constructing the Markdown message for Webex
        msg = (
            f"{status_emoji} **K-Guard Security Scan Report**\n\n"
            f"**Target Image:** `{image}`\n"
            f"**Critical Vulnerabilities:** {summary['critical']}\n"
            f"**High Vulnerabilities:** {summary['high']}\n"
            f"**Security Status:** {'🔴 Action Required' if summary['critical'] > 0 else '🟢 Compliant'}"
        )
        
        try:
            # Perform the POST request to Cisco Webex API
            requests.post(self.api_url, 
                          json={"roomId": self.room_id, "markdown": msg},
                          headers={"Authorization": f"Bearer {self.token}"}, 
                          timeout=5)
        except Exception as e:
            # Failure to notify shouldn't crash the main scanning process
            print(f"❌ Webex Notification Error: {e}")