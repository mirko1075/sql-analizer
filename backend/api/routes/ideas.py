from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import os

from .context import fetch_context_for_query
import backend.core.clients as clients

router = APIRouter()


class IdeaRequest(BaseModel):
    idea_text: str


@router.post("/api/v1/ideas/analyze")
def analyze_idea(req: IdeaRequest):
    try:
        # 1. Recupera contesto semantico
        context_data = fetch_context_for_query(req.idea_text)

        # 2. Prepara il prompt
        context = "\n\n".join([d.get("content", "") for d in context_data])
        prompt = f"""
You are DBPowerAI’s analysis engine.
Analyze the following idea for technical relevance and integration potential.

Context from documentation:
{context}

Idea:
{req.idea_text}

Return JSON with:
- summary
- relevance_score (0–100)
- suggested_feature
- reasoning
"""

        # 3. Richiama GPT
        client = clients.get_openai_client()
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": prompt}],
            response_format="json"
        )

        # response.output_parsed may or may not exist depending on SDK version. Fall back to text parse.
        parsed = getattr(response, "output_parsed", None)
        if parsed:
            return parsed

        # Try to extract JSON text from the response
        outputs = getattr(response, "output", [])
        if outputs and isinstance(outputs, list):
            # The SDK may return a list of message dicts with 'content'
            for item in outputs:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content")
                    if isinstance(content, dict):
                        # content may include 'text'
                        text = content.get("text")
                        if text:
                            return text

        return {"raw": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
