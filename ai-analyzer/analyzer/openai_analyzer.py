"""
OpenAI-based SQL analyzer implementation.
Supports OpenAI API and compatible endpoints.
"""
import json
import logging
from typing import Dict, Any
import requests

from .base import BaseAnalyzer
from models.schemas import AnalysisRequest
from config import ModelConfig

logger = logging.getLogger(__name__)


class OpenAIAnalyzer(BaseAnalyzer):
    """
    SQL analyzer using OpenAI API.

    Supports:
    - OpenAI official API (gpt-4, gpt-3.5-turbo)
    - Azure OpenAI
    - OpenAI-compatible APIs
    """

    def __init__(self, model_config: ModelConfig):
        """
        Initialize OpenAI analyzer.

        Args:
            model_config: Model configuration

        Raises:
            ValueError: If API key is missing
        """
        super().__init__(model_config.model_name)

        if not model_config.api_key:
            raise ValueError("OpenAI API key is required")

        self.api_key = model_config.api_key
        self.api_base_url = model_config.api_base_url or "https://api.openai.com/v1"
        self.temperature = model_config.temperature
        self.max_tokens = model_config.max_tokens
        self.timeout = model_config.timeout

    def _analyze_with_ai(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Analyze SQL query using OpenAI API.

        Args:
            request: Analysis request

        Returns:
            Dictionary with analysis results

        Raises:
            Exception: If API call fails
        """
        system_prompt = self.get_system_prompt(request.database_type or "postgresql")

        # Build user message with query details
        user_message = self._build_user_message(request)

        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}  # Request JSON response
        }

        try:
            logger.debug(f"Calling OpenAI API: {self.api_base_url}/chat/completions")

            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()

            # Extract AI response
            if "choices" not in result or len(result["choices"]) == 0:
                raise Exception("No response from OpenAI API")

            content = result["choices"][0]["message"]["content"]

            # Parse JSON response
            try:
                analysis_result = json.loads(content)
                return analysis_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response content: {content}")
                # Return empty issues if parsing fails
                return {"issues": []}

        except requests.exceptions.Timeout:
            logger.error(f"OpenAI API timeout after {self.timeout}s")
            raise Exception("AI analysis timeout")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
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
            f"Database: {request.database_type or 'Unknown'}",
            f"\nSQL Query:\n```sql\n{request.sql_query}\n```"
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
            message_parts.append(f"\nAdditional Context: {json.dumps(request.metadata, indent=2)}")

        message_parts.append("\nPlease analyze this query and identify any performance issues.")

        return "\n".join(message_parts)
