"""
Factory for creating AI analyzer instances.
"""
import logging
from typing import Optional

from .base import BaseAnalyzer
from .openai_analyzer import OpenAIAnalyzer
from .local_analyzer import LocalAnalyzer
from .stub_analyzer import StubAnalyzer
from config import ModelConfig, ModelProvider

logger = logging.getLogger(__name__)


def create_analyzer(model_config: ModelConfig) -> BaseAnalyzer:
    """
    Create appropriate analyzer based on model configuration.

    Args:
        model_config: Model configuration

    Returns:
        Analyzer instance

    Raises:
        ValueError: If provider is unknown or configuration is invalid
    """
    logger.info(f"Creating analyzer for provider: {model_config.provider}, model: {model_config.model_name}")

    if model_config.provider == ModelProvider.OPENAI:
        return OpenAIAnalyzer(model_config)

    elif model_config.provider == ModelProvider.OLLAMA:
        return LocalAnalyzer(model_config)

    elif model_config.provider == ModelProvider.ANTHROPIC:
        # Future: implement Anthropic analyzer
        raise ValueError("Anthropic provider not yet implemented")

    elif model_config.provider == ModelProvider.STUB:
        return StubAnalyzer(model_config)

    else:
        raise ValueError(f"Unknown model provider: {model_config.provider}")


_global_analyzer: Optional[BaseAnalyzer] = None


def get_analyzer(model_config: Optional[ModelConfig] = None) -> BaseAnalyzer:
    """
    Get global analyzer instance (singleton pattern).

    Args:
        model_config: Model configuration (required for first call)

    Returns:
        Analyzer instance

    Raises:
        ValueError: If analyzer not initialized and no config provided
    """
    global _global_analyzer

    if _global_analyzer is None:
        if model_config is None:
            raise ValueError("Analyzer not initialized. Provide model_config on first call.")
        _global_analyzer = create_analyzer(model_config)

    return _global_analyzer


def reset_analyzer():
    """Reset global analyzer instance."""
    global _global_analyzer
    _global_analyzer = None
