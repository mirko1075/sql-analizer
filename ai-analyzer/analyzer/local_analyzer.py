"""
Local/Ollama-based SQL analyzer implementation.
Supports on-premise deployment with local models.
"""
import json
import logging
from typing import Dict, Any
import requests

from .base import BaseAnalyzer
from models.schemas import AnalysisRequest
from config import ModelConfig

logger = logging.getLogger(__name__)


class LocalAnalyzer(BaseAnalyzer):
    """
    SQL analyzer using local models via Ollama.

    Supports:
    - Ollama local models (llama2, codellama, mistral, etc.)
    - Any OpenAI-compatible local endpoint
    """

    def __init__(self, model_config: ModelConfig):
        """
        Initialize local analyzer.

        Args:
            model_config: Model configuration

        Raises:
            ValueError: If API base URL is missing
        """
        super().__init__(model_config.model_name)

        if not model_config.api_base_url:
            raise ValueError("API base URL is required for local models (e.g., http://localhost:11434)")

        self.api_base_url = model_config.api_base_url.rstrip('/')
        self.temperature = model_config.temperature
        self.max_tokens = model_config.max_tokens
        self.timeout = model_config.timeout

    def _analyze_with_ai(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Analyze SQL query using local model via Ollama.

        Args:
            request: Analysis request

        Returns:
            Dictionary with analysis results

        Raises:
            Exception: If API call fails
        """
        system_prompt = self.get_system_prompt(request.database_type or "postgresql")
        user_message = self._build_user_message(request)

        # Prepare Ollama API request
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\n{user_message}",
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            },
            "format": "json"  # Request JSON response
        }

        try:
            logger.debug(f"Calling Ollama API: {self.api_base_url}/api/generate")

            response = requests.post(
                f"{self.api_base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()

            # Extract response from Ollama format
            if "response" not in result:
                raise Exception("No response from Ollama API")

            content = result["response"]

            # Parse JSON response
            try:
                analysis_result = json.loads(content)
                return analysis_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response content: {content}")

                # Try to extract JSON from markdown code blocks if present
                if "```json" in content:
                    try:
                        json_start = content.index("```json") + 7
                        json_end = content.index("```", json_start)
                        json_str = content[json_start:json_end].strip()
                        analysis_result = json.loads(json_str)
                        return analysis_result
                    except Exception:
                        pass

                # Return empty issues if parsing fails
                return {"issues": []}

        except requests.exceptions.Timeout:
            logger.error(f"Ollama API timeout after {self.timeout}s")
            raise Exception("AI analysis timeout - local model may be slow or unavailable")

        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to Ollama at {self.api_base_url}")
            raise Exception("Cannot connect to local model - ensure Ollama is running")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise Exception(f"AI analysis failed: {str(e)}")

    def _build_user_message(self, request: AnalysisRequest) -> str:
        """
        Build user message with query details.

        Args:
            request: Analysis request

        Returns:
            Formatted user message
        """
        message_parts = [
            f"Database Type: {request.database_type or 'Unknown'}",
            f"\nSQL Query to Analyze:\n```sql\n{request.sql_query}\n```"
        ]

        # Add execution metrics if available
        if request.execution_time_ms is not None:
            message_parts.append(f"\nExecution Time: {request.execution_time_ms:.2f}ms")

        if request.rows_examined is not None:
            message_parts.append(f"Rows Examined: {request.rows_examined:,}")

        if request.rows_returned is not None:
            message_parts.append(f"Rows Returned: {request.rows_returned:,}")

        # Add metadata if present
        if request.metadata:
            message_parts.append(f"\nAdditional Information: {json.dumps(request.metadata, indent=2)}")

        message_parts.append("\nAnalyze this SQL query for performance issues and return results in JSON format.")

        return "\n".join(message_parts)

    def check_health(self) -> bool:
        """
        Check if local model is available.

        Returns:
            True if model is available and responding
        """
        try:
            # Try to list available models
            response = requests.get(
                f"{self.api_base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()

            models = response.json()

            # Check if our model is available
            if "models" in models:
                available_models = [m["name"] for m in models["models"]]
                if self.model_name in available_models:
                    logger.info(f"Model {self.model_name} is available")
                    return True
                else:
                    logger.warning(f"Model {self.model_name} not found. Available: {available_models}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
