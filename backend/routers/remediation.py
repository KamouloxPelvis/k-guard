from fastapi import APIRouter, Depends, HTTPException, Body
from .auth import verify_token
from database import v1, apps_client
from metrics_manager import scale_down_deployment
from pydantic import BaseModel
import datetime

router = APIRouter(prefix="/remediation", tags=["Management"])

class PatchImagePayload(BaseModel):
    namespace: str
    deployment: str
    new_image: str

import datetime

@router.post("/restart/{namespace}/{deployment_name}")
async def restart_deployment(namespace: str, deployment_name: str, user: dict = Depends(verify_token)):
    """Déclenche un Rolling Restart propre via une annotation (Méthode SRE)"""
    try:
        # On ajoute une annotation avec l'heure pour forcer le restart
        now = datetime.datetime.now().isoformat()
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now
                        }
                    }
                }
            }
        }
        apps_client.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=body)
        print(f"🚀 [K-GUARD] Patch appliqué sur le déploiement {deployment_name} ({namespace})")
        return {"status": "success", "message": f"Rolling restart lancé pour {deployment_name}"}    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/remediate/{namespace}/{pod_name}")
async def remediate_pod(namespace: str, pod_name: str, user: dict = Depends(verify_token)):
    """Déclenche une remédiation SRE (Scale Down à 0)"""
    try:
        # On s'assure que scale_down_deployment gère bien l'in-cluster config
        result = await scale_down_deployment(namespace, pod_name)
        return result   
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de remédiation : {str(e)}")

@router.post("/patch-image")
async def patch_deployment_image(
    payload: PatchImagePayload, # Utilisation de Pydantic pour la validation
    user: dict = Depends(verify_token)
):
    """
    Met à jour l'image d'un déploiement (Mise à jour de sécurité)
    """
    try:
        # 1. On récupère le déploiement
        deployment = apps_client.read_namespaced_deployment(name=payload.deployment, namespace=payload.namespace)
        
        # 2. On identifie dynamiquement le conteneur (plus robuste)
        # On cherche un conteneur qui n'est pas un 'sidecar' ou on prend le premier si un seul
        container_name = deployment.spec.template.spec.containers[0].name
        if len(deployment.spec.template.spec.containers) > 1:
             # Si plusieurs conteneurs, on peut loguer pour debug ou affiner la logique
             print(f"⚠️ Multi-container detected for {payload.deployment}, patching first: {container_name}")

        # 3. Application du patch stratégique (Strategic Merge Patch)
        body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": container_name,
                                "image": payload.new_image
                            }
                        ]
                    }
                }
            }
        }

        apps_client.patch_namespaced_deployment(
            name=payload.deployment,
            namespace=payload.namespace,
            body=body
        )

        return {
            "status": "success", 
            "message": f"Update vers {payload.new_image} en cours..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patch-logs/{namespace}/{deployment_name}")
async def get_patch_events(namespace: str, deployment_name: str, user: dict = Depends(verify_token)):
    """Récupère les derniers événements K3s liés au déploiement"""
    try:
        events = v1.list_namespaced_event(namespace)
        # Filtrage intelligent sur les événements liés au déploiement
        relevant_events = [
            f"[{e.last_timestamp.strftime('%H:%M:%S') if e.last_timestamp else '?'}] {e.message}" 
            for e in events.items 
            if e.involved_object and deployment_name in e.involved_object.name
        ]
        return {"logs": "\n".join(relevant_events[-15:])}
    except Exception as e:
        return {"logs": f"Erreur de lecture des événements : {str(e)}"}