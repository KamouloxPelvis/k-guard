from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter(prefix="/security", tags=["Runtime Security"])

ELASTICSEARCH_URL = "http://elasticsearch-master:9200"

@router.get("/alerts")
async def get_runtime_alerts():
    """
    Fetches real-time runtime security alerts from Elasticsearch.
    Standardized access for Cisco-compliant audit reporting.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Querying the falco index directly
            response = await client.post(
                f"{ELASTICSEARCH_URL}/falco-*/_search",
                json={
                    "size": 50,
                    "sort": [{"@timestamp": {"order": "desc"}}],
                    "query": {"match_all": {}}
                }
            )
            response.raise_for_status()
            return response.json()["hits"]["hits"]
        except Exception as e:
            # Logging error for infrastructure debugging
            raise HTTPException(status_code=500, detail=f"Security stack unreachable: {str(e)}")