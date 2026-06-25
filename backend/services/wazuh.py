import httpx
import os

class WazuhService:
    def __init__(self):
        # Ces variables seront injectées depuis ton .env ou ton Kubernetes Secret
        self.base_url = os.getenv("WAZUH_API_URL", "https://wazuh-manager:55000")
        self.username = os.getenv("WAZUH_USERNAME", "admin")
        self.password = os.getenv("WAZUH_PASSWORD", "secret")
        self.token = None

    async def authenticate(self):
        """Récupère le token JWT pour l'API Wazuh."""
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.base_url}/security/user/authenticate",
                auth=(self.username, self.password)
            )
            if response.status_code == 200:
                self.token = response.json().get("data", {}).get("token")
            else:
                raise Exception("Impossible de s'authentifier auprès de Wazuh")

    async def get_latest_alerts(self, limit=10):
        """Récupère les dernières alertes de sécurité."""
        if not self.token:
            await self.authenticate()
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = await client.get(
                f"{self.base_url}/alerts?limit={limit}&sort=-timestamp",
                headers=headers
            )
            return response.json().get("data", {}).get("affected_items", [])