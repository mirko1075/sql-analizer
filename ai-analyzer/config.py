"""
Configuration for AI Analyzer service.
Supports both cloud models (OpenAI) and on-premise models (Ollama).
"""
import os
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """AI model providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    STUB = "stub"  # Mock analyzer for testing


class ModelConfig(BaseModel):
    """Configuration for AI model."""
    provider: ModelProvider = Field(default=ModelProvider.OPENAI)
    model_name: str = Field(default="gpt-4")
    api_key: Optional[str] = Field(default=None)
    api_base_url: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=100000)
    timeout: int = Field(default=60, ge=1, le=300)


class AnalyzerConfig(BaseModel):
    """Configuration for AI Analyzer service."""

    # Service settings
    service_name: str = Field(default="dbpower-ai-analyzer")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=16)

    # AI Model configuration
    model: ModelConfig = Field(default_factory=ModelConfig)

    # Analysis settings
    max_query_length: int = Field(default=10000, ge=1, le=100000)
    enable_caching: bool = Field(default=True)
    cache_ttl: int = Field(default=3600, ge=0)  # seconds

    # Security
    api_key_header: str = Field(default="X-API-Key")
    require_authentication: bool = Field(default=True)
    allowed_api_keys: list[str] = Field(default_factory=list)

    # Logging
    log_level: str = Field(default="INFO")
    log_queries: bool = Field(default=False)  # Privacy: don't log queries by default

    @classmethod
    def from_env(cls) -> "AnalyzerConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            # Service
            ANALYZER_HOST: Service host (default: 0.0.0.0)
            ANALYZER_PORT: Service port (default: 8001)
            ANALYZER_WORKERS: Number of workers (default: 1)

            # AI Model
            MODEL_PROVIDER: openai, ollama, anthropic (default: openai)
            MODEL_NAME: Model name (default: gpt-4)
            MODEL_API_KEY: API key for cloud providers
            MODEL_API_BASE_URL: Custom API endpoint (for Ollama, etc.)
            MODEL_TEMPERATURE: Temperature (default: 0.7)
            MODEL_MAX_TOKENS: Max tokens (default: 2000)

            # Analysis
            MAX_QUERY_LENGTH: Max SQL query length (default: 10000)
            ENABLE_CACHING: Enable result caching (default: true)
            CACHE_TTL: Cache TTL in seconds (default: 3600)

            # Security
            REQUIRE_AUTHENTICATION: Require API key (default: true)
            ALLOWED_API_KEYS: Comma-separated list of allowed API keys

            # Logging
            LOG_LEVEL: Logging level (default: INFO)
            LOG_QUERIES: Log SQL queries (default: false)

        Returns:
            AnalyzerConfig instance
        """
        # Model configuration
        model_config = ModelConfig(
            provider=ModelProvider(os.getenv("MODEL_PROVIDER", "openai")),
            model_name=os.getenv("MODEL_NAME", "gpt-4"),
            api_key=os.getenv("MODEL_API_KEY"),
            api_base_url=os.getenv("MODEL_API_BASE_URL"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MODEL_MAX_TOKENS", "2000")),
            timeout=int(os.getenv("MODEL_TIMEOUT", "60")),
        )

        # Parse allowed API keys
        allowed_keys_str = os.getenv("ALLOWED_API_KEYS", "")
        allowed_keys = [k.strip() for k in allowed_keys_str.split(",") if k.strip()]

        return cls(
            host=os.getenv("ANALYZER_HOST", "0.0.0.0"),
            port=int(os.getenv("ANALYZER_PORT", "8001")),
            workers=int(os.getenv("ANALYZER_WORKERS", "1")),
            model=model_config,
            max_query_length=int(os.getenv("MAX_QUERY_LENGTH", "10000")),
            enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            cache_ttl=int(os.getenv("CACHE_TTL", "3600")),
            require_authentication=os.getenv("REQUIRE_AUTHENTICATION", "true").lower() == "true",
            allowed_api_keys=allowed_keys,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_queries=os.getenv("LOG_QUERIES", "false").lower() == "true",
        )


# Global configuration instance
config: Optional[AnalyzerConfig] = None


def get_config() -> AnalyzerConfig:
    """
    Get global configuration instance.

    Returns:
        AnalyzerConfig instance
    """
    global config
    if config is None:
        config = AnalyzerConfig.from_env()
    return config


def set_config(new_config: AnalyzerConfig):
    """
    Set global configuration instance.

    Args:
        new_config: New configuration
    """
    global config
    config = new_config
