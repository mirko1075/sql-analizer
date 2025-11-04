"""Factory for creating AI provider instances."""

import logging
from typing import Optional, Dict, Any

from .base_provider import BaseAIProvider
from .llama_provider import LLaMAProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)

# Singleton instance
_ai_provider: Optional[BaseAIProvider] = None


class AIProviderFactory:
    """Factory for creating AI provider instances."""
    
    @staticmethod
    def create_provider(provider_type: str, config: Dict[str, Any]) -> BaseAIProvider:
        """
        Create an AI provider instance.
        
        Args:
            provider_type: Type of provider ("llama", "openai", "anthropic")
            config: Configuration dictionary for the provider
            
        Returns:
            BaseAIProvider instance
            
        Raises:
            ValueError: If provider type is unknown
        """
        provider_type = provider_type.lower()
        
        # Log privacy warnings for cloud providers
        if provider_type in ["openai", "anthropic"]:
            logger.warning(
                f"\n{'='*80}\n"
                f"⚠️  PRIVACY WARNING: Using {provider_type.upper()} provider\n"
                f"{'='*80}\n"
                f"SQL queries and database schema information will be sent to external APIs:\n"
                f"  - OpenAI: https://api.openai.com\n" if provider_type == "openai" else
                f"  - Anthropic: https://api.anthropic.com\n"
                f"\n"
                f"This data will be transmitted over the internet and processed by third-party services.\n"
                f"Ensure compliance with your organization's data privacy policies.\n"
                f"\n"
                f"For complete privacy, use AI_PROVIDER=llama (100% local processing).\n"
                f"{'='*80}\n"
            )
        
        if provider_type == "llama":
            logger.info("✅ Using LLaMA provider (100% local, no external data transmission)")
            return LLaMAProvider(config)
        elif provider_type == "openai":
            return OpenAIProvider(config)
        elif provider_type == "anthropic":
            return AnthropicProvider(config)
        else:
            raise ValueError(
                f"Unknown AI provider: {provider_type}. "
                f"Supported providers: llama, openai, anthropic"
            )


def get_ai_provider() -> BaseAIProvider:
    """
    Get the singleton AI provider instance.
    
    This function is lazy-initialized and will create the provider
    on first call based on environment configuration.
    
    Returns:
        BaseAIProvider instance
    """
    global _ai_provider
    
    if _ai_provider is None:
        # Import here to avoid circular imports
        from core.config import settings
        
        # Build config from settings
        config = {
            "log_requests": settings.ai_log_requests,
            "timeout": settings.ai_timeout,
            "max_retries": settings.ai_max_retries,
        }
        
        # Add provider-specific config
        if settings.ai_provider == "llama":
            config.update({
                "base_url": settings.llama_base_url,
                "model": settings.llama_model,
            })
        elif settings.ai_provider == "openai":
            config.update({
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
                "base_url": settings.openai_base_url,
                "max_tokens": settings.openai_max_tokens,
            })
        elif settings.ai_provider == "anthropic":
            config.update({
                "api_key": settings.anthropic_api_key,
                "model": settings.anthropic_model,
                "base_url": settings.anthropic_base_url,
                "max_tokens": settings.anthropic_max_tokens,
            })
        
        _ai_provider = AIProviderFactory.create_provider(settings.ai_provider, config)
        logger.info(f"AI provider initialized: {settings.ai_provider}")
    
    return _ai_provider


async def check_provider_health() -> bool:
    """
    Check if the current AI provider is healthy.
    
    Returns:
        True if healthy, False otherwise
    """
    try:
        provider = get_ai_provider()
        return await provider.check_health()
    except Exception as e:
        logger.error(f"Provider health check failed: {str(e)}")
        return False
