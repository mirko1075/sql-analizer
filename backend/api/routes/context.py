from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from typing import Any, Dict, List
import backend.core.clients as clients

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


def fetch_context_for_query(query: str, match_threshold: float = 0.75, match_count: int = 5) -> List[Dict[str, Any]]:
    """Return the top matching documents from the Supabase vector store for a given query.

    This helper is separated from the router so other modules (ideas analyzer) can reuse it
    without triggering circular import issues.
    """
    try:
        client = clients.get_openai_client()
        supabase = clients.get_supabase_client()

        embedding_resp = client.embeddings.create(model="text-embedding-3-small", input=query)
        embedding = embedding_resp.data[0].embedding

        res = supabase.rpc("match_project_docs", {
            "query_embedding": embedding,
            "match_threshold": match_threshold,
            "match_count": match_count
        }).execute()

        return res.data or []
    except Exception:
        # Let caller handle HTTP-level translation
        raise


@router.post("/api/v1/context/query")
def get_context(req: QueryRequest):
    try:
        data = fetch_context_for_query(req.query)
        return {"context": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
