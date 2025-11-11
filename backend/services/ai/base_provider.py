"""Base provider interface for AI query analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisRequest:
    """Request object for AI analysis."""
    sql_query: str
    explain_plan: Optional[str] = None
    schema_info: Optional[Dict[str, Any]] = None
    table_stats: Optional[Dict[str, Any]] = None
    lock_info: Optional[str] = None
    index_info: Optional[Dict[str, Any]] = None


@dataclass
class AIAnalysisResponse:
    """Response object from AI analysis."""
    analysis: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def analyze_query(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Analyze a SQL query and return suggestions.
        
        Args:
            request: AIAnalysisRequest containing query and context
            
        Returns:
            AIAnalysisResponse with analysis and metadata
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if the AI provider is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def _build_prompt(self, request: AIAnalysisRequest) -> str:
        """
        Build a comprehensive prompt for AI analysis.
        
        Args:
            request: AIAnalysisRequest containing query and context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are a MySQL performance expert. Analyze the following slow query and provide specific recommendations.",
            "",
            "**SQL Query:**",
            f"```sql\n{request.sql_query}\n```",
        ]
        
        if request.explain_plan:
            prompt_parts.extend([
                "",
                "**EXPLAIN Output:**",
                f"```\n{request.explain_plan}\n```",
            ])
        
        if request.schema_info:
            prompt_parts.extend([
                "",
                "**Table Schema:**",
                f"```\n{request.schema_info}\n```",
            ])
        
        if request.index_info:
            prompt_parts.extend([
                "",
                "**Current Indexes:**",
                f"```\n{request.index_info}\n```",
            ])
        
        if request.table_stats:
            prompt_parts.extend([
                "",
                "**Table Statistics:**",
                f"```\n{request.table_stats}\n```",
            ])
        
        if request.lock_info:
            prompt_parts.extend([
                "",
                "**Lock Information:**",
                f"```\n{request.lock_info}\n```",
            ])
        
        prompt_parts.extend([
            "",
            "**Provide:**",
            "1. Root cause analysis of performance issues",
            "2. Specific index recommendations (if applicable)",
            "3. Query rewrite suggestions (if applicable)",
            "4. Configuration tuning recommendations",
            "5. Priority level (High/Medium/Low)",
            "",
            "Be specific and actionable. Format your response in clear sections."
        ])
        
        return "\n".join(prompt_parts)
    
    def _log_request(self, request: AIAnalysisRequest, provider: str, model: str):
        """
        Log the AI request for audit purposes.
        
        Args:
            request: AIAnalysisRequest being sent
            provider: Provider name
            model: Model being used
        """
        if self.config.get("log_requests", True):
            self.logger.info(
                f"AI Request | Provider: {provider} | Model: {model} | "
                f"Query length: {len(request.sql_query)} chars | "
                f"Has EXPLAIN: {request.explain_plan is not None} | "
                f"Has schema: {request.schema_info is not None}"
            )
    
    def _log_response(self, response: AIAnalysisResponse):
        """
        Log the AI response for audit purposes.
        
        Args:
            response: AIAnalysisResponse received
        """
        if self.config.get("log_requests", True):
            self.logger.info(
                f"AI Response | Provider: {response.provider} | Model: {response.model} | "
                f"Duration: {response.duration_ms:.2f}ms | "
                f"Tokens: {response.tokens_used or 'N/A'} | "
                f"Analysis length: {len(response.analysis)} chars | "
                f"Error: {response.error or 'None'}"
            )
