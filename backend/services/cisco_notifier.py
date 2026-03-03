import requests
import os

class CiscoWebexNotifier:
    def __init__(self):
        self.token = os.getenv("WEBEX_BOT_TOKEN")
        self.room_id = os.getenv("WEBEX_ROOM_ID")
        self.enabled = os.getenv("WEBEX_ENABLED", "false").lower() == "true"
        self.api_url = "https://webexapis.com/v1/messages"

    def send_scan_report(self, image, summary):
        if not self.enabled or not self.token:
            return
        
        status_emoji = "🚨" if summary['critical'] > 0 else "✅"
        msg = (
            f"{status_emoji} **K-Guard Scan Report**\n\n"
            f"**Image:** `{image}`\n"
            f"**Critiques:** {summary['critical']}\n"
            f"**Hautes:** {summary['high']}\n"
            f"**Status:** {'Action Required' if summary['critical'] > 0 else 'Compliant'}"
        )
        
        try:
            requests.post(self.api_url, 
                          json={"roomId": self.room_id, "markdown": msg},
                          headers={"Authorization": f"Bearer {self.token}"}, 
                          timeout=5)
        except Exception as e:
            print(f"❌ Webex Notification Error: {e}")