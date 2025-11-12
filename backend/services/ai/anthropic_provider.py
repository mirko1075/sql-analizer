"""Anthropic Claude provider for cloud-based AI inference."""

import httpx
import time
from typing import Dict, Any

from .base_provider import BaseAIProvider, AIAnalysisRequest, AIAnalysisResponse


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider (cloud-based)."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider."""
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")
        
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")
        self.model = config.get("model", "claude-3-sonnet-20240229")
        self.timeout = config.get("timeout", 60.0)
        self.max_tokens = config.get("max_tokens", 2000)
    
    async def analyze_query(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Analyze query using Anthropic Claude.
        
        Args:
            request: AIAnalysisRequest containing query and context
            
        Returns:
            AIAnalysisResponse with analysis
        """
        start_time = time.time()
        prompt = self._build_prompt(request)
        self._log_request(request, "anthropic", self.model)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": self.max_tokens,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "system": "You are an expert MySQL database performance analyst. Provide clear, actionable recommendations based on query analysis.",
                        "temperature": 0.1,
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract response
                content_blocks = data.get("content", [])
                analysis = ""
                if content_blocks:
                    analysis = content_blocks[0].get("text", "")
                
                usage = data.get("usage", {})
                
                result = AIAnalysisResponse(
                    analysis=analysis,
                    provider="anthropic",
                    model=data.get("model", self.model),
                    tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    duration_ms=duration_ms,
                )
                
                self._log_response(result)
                return result
                
        except httpx.TimeoutException as e:
            error_msg = f"Anthropic request timeout after {self.timeout}s"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="anthropic",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"Anthropic API HTTP error: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="anthropic",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Anthropic API error: {str(e)}"
            self.logger.error(error_msg)
            return AIAnalysisResponse(
                analysis="",
                provider="anthropic",
                model=self.model,
                duration_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )
    
    async def check_health(self) -> bool:
        """
        Check if Anthropic API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Anthropic doesn't have a simple health check endpoint,
            # so we'll do a minimal request to verify API key
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "test"}]
                    }
                )
                response.raise_for_status()
                
                self.logger.info(f"Anthropic provider healthy. Model: {self.model}")
                return True
        except Exception as e:
            self.logger.error(f"Anthropic health check failed: {str(e)}")
            return False
