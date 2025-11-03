"""
AI LLaMA Client for query analysis.
Communicates with local Ollama instance to get AI-powered optimization suggestions.
"""
import requests
import json
from typing import Optional, Dict, Any

from backend.core.config import settings
from backend.core.logger import setup_logger

logger = setup_logger(__name__, settings.log_level)


def check_llama_health() -> bool:
    """
    Check if LLaMA/Ollama service is available.
    
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        response = requests.get(f"{settings.ai_base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"LLaMA service not available: {e}")
        return False


def ensure_model_loaded() -> bool:
    """
    Ensure the LLaMA model is pulled/loaded.
    
    Returns:
        True if model is ready, False otherwise
    """
    try:
        # Check if model exists
        response = requests.get(f"{settings.ai_base_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if settings.ai_model in model_names or any(settings.ai_model in name for name in model_names):
                logger.info(f"Model {settings.ai_model} is already loaded")
                return True
        
        # Pull the model if not exists
        logger.info(f"Pulling model {settings.ai_model}...")
        pull_response = requests.post(
            f"{settings.ai_base_url}/api/pull",
            json={"name": settings.ai_model},
            stream=True,
            timeout=300
        )
        
        # Stream the response to track progress
        for line in pull_response.iter_lines():
            if line:
                data = json.loads(line)
                if "status" in data:
                    logger.info(f"Pull status: {data['status']}")
        
        logger.info(f"Model {settings.ai_model} pulled successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring model loaded: {e}", exc_info=True)
        return False


def analyze_with_llama(sql: str, explain_plan: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Analyze SQL query using LLaMA model.
    
    Args:
        sql: SQL query text
        explain_plan: Optional EXPLAIN output
        context: Optional additional context (query time, rows examined, etc.)
    
    Returns:
        AI analysis text with optimization suggestions
    """
    if not check_llama_health():
        return "AI service is not available. Please ensure Ollama container is running."
    
    # Build the prompt
    prompt = f"""You are an expert SQL performance optimizer.
Analyze this query and provide specific, actionable optimization suggestions.

Query:
```sql
{sql}
```
"""
    
    if explain_plan:
        prompt += f"\nEXPLAIN output:\n{explain_plan}\n"
    
    if context:
        prompt += f"\nQuery Performance Metrics:\n"
        if "query_time" in context:
            prompt += f"- Execution Time: {context['query_time']}s\n"
        if "rows_examined" in context:
            prompt += f"- Rows Examined: {context['rows_examined']}\n"
        if "rows_sent" in context:
            prompt += f"- Rows Sent: {context['rows_sent']}\n"
    
    prompt += """
Please provide:
1. Main performance issues identified
2. Specific index recommendations with CREATE INDEX statements
3. Query rewrite suggestions if applicable
4. Estimated impact of each optimization

Keep your response concise and actionable."""
    
    try:
        logger.info(f"Sending query to LLaMA for analysis...")
        
        response = requests.post(
            f"{settings.ai_base_url}/api/generate",
            json={
                "model": settings.ai_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more focused responses
                    "top_p": 0.9,
                    "top_k": 40
                }
            },
            timeout=120  # 2 minutes timeout for complex queries
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "")
            
            logger.info(f"Received AI analysis ({len(ai_response)} characters)")
            return ai_response
        else:
            error_msg = f"AI service returned status {response.status_code}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
            
    except requests.exceptions.Timeout:
        logger.error("AI request timed out")
        return "Error: AI analysis timed out. The query might be too complex."
    except Exception as e:
        logger.error(f"Error calling LLaMA API: {e}", exc_info=True)
        return f"Error: {str(e)}"


def get_quick_suggestions(sql: str) -> str:
    """
    Get quick optimization suggestions without full analysis.
    Useful for batch processing.
    
    Args:
        sql: SQL query text
    
    Returns:
        Quick suggestions text
    """
    prompt = f"""Briefly analyze this SQL query and list 2-3 main optimization suggestions:

```sql
{sql}
```

Be concise - just bullet points."""
    
    try:
        response = requests.post(
            f"{settings.ai_base_url}/api/generate",
            json={
                "model": settings.ai_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200  # Limit response length
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            return "Quick analysis unavailable"
            
    except Exception as e:
        logger.error(f"Error in quick suggestions: {e}")
        return "Quick analysis failed"
