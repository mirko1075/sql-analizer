"""OpenAI provider for cloud-based AI inference."""

import httpx
import time
from typing import Dict, Any

from .base_provider import BaseAIProvider, AIAnalysisRequest, AIAnalysisResponse


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT provider (cloud-based)."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider."""
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4-turbo-preview")
        self.timeout = config.get("timeout", 60.0)
        self.max_tokens = config.get("max_tokens", 2000)
    
    async def analyze_query(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Analyze query using OpenAI GPT.
        
        Args:
            request: AIAnalysisRequest containing query and context
            
        Returns:
            AIAnalysisResponse with analysis
        """
        start_time = time.time()
        prompt = self._build_prompt(request)
        self._log_request(request, "openai", self.model)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert MySQL database performance analyst. Provide clear, actionable recommendations."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": self.max_tokens,
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract response
                analysis = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                
                result = AIAnalysisResponse(
                    analysis=analysis,
                    provider="openai",
                    model=data.get("model", self.model),
                    tokens_used=usage.get("total_tokens"),
                    duration_ms=duration_ms,
                )
                
                self._log_response(result)
                return result
                
        except httpx.TimeoutException as e:
            error_msg = f"OpenAI request timeout after {self.timeout}s"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="openai",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="openai",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"OpenAI API error: {str(e)}"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="openai",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
    
    async def check_health(self) -> bool:
        """
        Check if OpenAI API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    }
                )
                response.raise_for_status()
                
                self.logger.info(f"OpenAI provider healthy. Model: {self.model}")
                return True
        except Exception as e:
            self.logger.error(f"OpenAI health check failed: {str(e)}")
            return False
