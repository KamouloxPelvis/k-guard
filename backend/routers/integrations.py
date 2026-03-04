from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import database

router = APIRouter(tags=["Integrations"])

class WebexConfig(BaseModel):
    enabled: bool
    token: str
    room_id: str

@router.get("/settings/integrations/webex")
async def get_webex_status():
    """
    Récupère la configuration actuelle pour l'affichage Frontend.
    """
    try:
        settings = database.get_integration_settings("webex")
        if not settings:
            return {"enabled": False, "configured": False}
        
        # On ne renvoie jamais le token complet pour la sécurité (DevSecOps !)
        # On renvoie juste un booléen et éventuellement la fin du token pour rassurer l'user
        return {
            "enabled": bool(settings['enabled']),
            "configured": bool(settings['token']),
            "room_id": settings['target_id'] or "",
            "token_preview": f"***{settings['token'][-4:]}" if settings['token'] else ""
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/integrations/webex")
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
