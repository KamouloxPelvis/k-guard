from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import backend.database

router = APIRouter(tags=["Integrations"])

class WebexConfig(BaseModel):
    enabled: bool
    token: str
    room_id: str

@router.get("/settings/integrations/webex")
async def get_webex_status():
    """
    Retrieves current configuration for Frontend display.
    """
    try:
        settings = backend.database.get_integration_settings("webex")
        if not settings:
            return {"enabled": False, "configured": False}
        
        # Security best practice (DevSecOps): Never return the full token to the frontend.
        # We return a boolean status and a masked preview for user verification.
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
    Configures Cisco Webex integration and performs a hot-reload of environment variables.
    """
    try:
        # 1. Update SQLite database
        conn = backend.database.sqlite3.connect(backend.database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE integrations 
            SET enabled = ?, token = ?, target_id = ?
            WHERE name = 'webex'
        ''', (1 if config.enabled else 0, config.token, config.room_id))
        conn.commit()
        conn.close()

        # 2. Update global state for CiscoWebexNotifier (Runtime synchronization)
        os.environ["WEBEX_ENABLED"] = str(config.enabled).lower()
        os.environ["WEBEX_BOT_TOKEN"] = config.token
        os.environ["WEBEX_ROOM_ID"] = config.room_id

        return {"status": "success", "message": "Cisco Webex integration synced"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))