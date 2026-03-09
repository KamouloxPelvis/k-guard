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

@router.post("/restart/{namespace}/{deployment_name}")
async def restart_deployment(namespace: str, deployment_name: str, user: dict = Depends(verify_token)):
    """Triggers a clean Rolling Restart using annotations (SRE best practice)"""
    try:
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
        print(f"🚀 [K-GUARD] Patch applied to deployment {deployment_name} ({namespace})")
        return {"status": "success", "message": f"Rolling restart initiated for {deployment_name}"}    
    except Exception as e:
        # Security: Log K8s API errors locally, return generic failure
        print(f"❌ [K8s API] Restart deployment failed: {e}")
        return {"status": "error", "message": "Failed to initiate rolling restart."}

@router.post("/remediate/{namespace}/{pod_name}")
async def remediate_pod(namespace: str, pod_name: str, user: dict = Depends(verify_token)):
    """Triggers an SRE remediation (Scale Down to 0)"""
    try:
        result = await scale_down_deployment(namespace, pod_name)
        return result   
    except Exception as e:
        print(f"❌ [K8s API] Pod remediation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error during pod remediation process.")

@router.post("/patch-image")
async def patch_deployment_image(
    payload: PatchImagePayload, 
    user: dict = Depends(verify_token)
):
    """Updates a deployment image (Security Patching)"""
    try:
        deployment = apps_client.read_namespaced_deployment(name=payload.deployment, namespace=payload.namespace)
        
        container_name = deployment.spec.template.spec.containers[0].name
        if len(deployment.spec.template.spec.containers) > 1:
             print(f"⚠️ Multi-container detected for {payload.deployment}, patching first: {container_name}")

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
            "message": f"Updating to {payload.new_image} in progress..."
        }
    except Exception as e:
        print(f"❌ [K8s API] Image patching failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply image patch to deployment.")

@router.get("/patch-logs/{namespace}/{deployment_name}")
async def get_patch_events(namespace: str, deployment_name: str, user: dict = Depends(verify_token)):
    """Retrieves the latest K3s events related to the deployment"""
    try:
        events = v1.list_namespaced_event(namespace)
        relevant_events = [
            f"[{e.last_timestamp.strftime('%H:%M:%S') if e.last_timestamp else '?'}] {e.message}" 
            for e in events.items 
            if e.involved_object and deployment_name in e.involved_object.name
        ]
        return {"logs": "\n".join(relevant_events[-15:])}
    except Exception as e:
        print(f"❌ [K8s API] Event log retrieval failed: {e}")
        return {"logs": "Error reading Kubernetes events from the cluster."}    