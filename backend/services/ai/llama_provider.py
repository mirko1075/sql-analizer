"""LLaMA/Ollama provider for local AI inference."""

import httpx
import time
from typing import Dict, Any

from .base_provider import BaseAIProvider, AIAnalysisRequest, AIAnalysisResponse


class LLaMAProvider(BaseAIProvider):
    """LLaMA provider using local Ollama server."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LLaMA provider."""
        super().__init__(config)
        self.base_url = config.get("base_url", "http://ai-llama:11434")
        self.model = config.get("model", "llama3")
        self.timeout = config.get("timeout", 120.0)
        self.max_retries = config.get("max_retries", 3)
    
    async def analyze_query(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Analyze query using local LLaMA/Ollama.
        
        Args:
            request: AIAnalysisRequest containing query and context
            
        Returns:
            AIAnalysisResponse with analysis
        """
        start_time = time.time()
        prompt = self._build_prompt(request)
        self._log_request(request, "llama", self.model)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistent technical advice
                            "top_p": 0.9,
                        }
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                duration_ms = (time.time() - start_time) * 1000
                
                result = AIAnalysisResponse(
                    analysis=data.get("response", ""),
                    provider="llama",
                    model=self.model,
                    tokens_used=data.get("eval_count"),
                    duration_ms=duration_ms,
                )
                
                self._log_response(result)
                return result
                
        except httpx.TimeoutException as e:
            error_msg = f"LLaMA request timeout after {self.timeout}s"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="llama",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"LLaMA API error: {str(e)}"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="llama",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
    
    async def check_health(self) -> bool:
        """
        Check if Ollama server is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
                # Check if our model is available
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                if self.model not in models:
                    self.logger.warning(f"Model {self.model} not found in Ollama. Available: {models}")
                    return False
                
                self.logger.info(f"LLaMA provider healthy. Model: {self.model}")
                return True
        except Exception as e:
            self.logger.error(f"LLaMA health check failed: {str(e)}")
            return False
