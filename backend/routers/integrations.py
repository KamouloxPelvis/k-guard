from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import database

router = APIRouter(tags=["Integrations"])

class WebexConfig(BaseModel):
    enabled: bool
    token: str
    room_id: str

@router.post("/integrations/webex")
async def update_webex(config: WebexConfig):
    """
    Configure l'intégration Cisco Webex et met à jour l'environnement à chaud.
    """
    try:
        # 1. Mise à jour SQLite
        conn = database.sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE integrations 
            SET enabled = ?, token = ?, target_id = ?
            WHERE name = 'webex'
        ''', (1 if config.enabled else 0, config.token, config.room_id))
        conn.commit()
        conn.close()

        # 2. Mise à jour de l'état global pour CiscoWebexNotifier
        os.environ["WEBEX_ENABLED"] = str(config.enabled).lower()
        os.environ["WEBEX_BOT_TOKEN"] = config.token
        os.environ["WEBEX_ROOM_ID"] = config.room_id

        return {"status": "success", "message": "Cisco Webex integration synced"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))