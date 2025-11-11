"""
Configuration for API Gateway.
Centralized routing and rate limiting for all DBPower services.
"""
import os
from typing import Dict, List
from pydantic import BaseModel, Field


class ServiceEndpoint(BaseModel):
    """Configuration for a backend service endpoint."""
    name: str
    url: str
    health_check_path: str = "/health"
    timeout: int = Field(default=30, ge=1, le=300)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration per organization."""
    requests_per_minute: int = Field(default=100, ge=1, le=10000)
    burst_size: int = Field(default=20, ge=1, le=1000)
    enable_per_organization: bool = Field(default=True)
    enable_per_ip: bool = Field(default=True)
    block_duration_seconds: int = Field(default=60, ge=1, le=3600)


class GatewayConfig(BaseModel):
    """Configuration for API Gateway service."""

    # Service settings
    service_name: str = Field(default="dbpower-api-gateway")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=4, ge=1, le=32)

    # Backend services
    backend_url: str = Field(default="http://backend:8000")
    ai_analyzer_url: str = Field(default="http://ai-analyzer:8001")

    # Redis for rate limiting and caching
    redis_url: str = Field(default="redis://redis:6379/0")
    redis_enabled: bool = Field(default=True)

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Authentication
    require_authentication: bool = Field(default=True)
    jwt_secret_key: str = Field(default="change-this-secret-key-in-production")
    jwt_algorithm: str = Field(default="HS256")

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_requests: bool = Field(default=True)
    log_response_body: bool = Field(default=False)  # Privacy

    # Health checks
    health_check_interval: int = Field(default=30, ge=5, le=300)

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            # Service
            GATEWAY_HOST: Service host (default: 0.0.0.0)
            GATEWAY_PORT: Service port (default: 8000)
            GATEWAY_WORKERS: Number of workers (default: 4)

            # Backend services
            BACKEND_URL: Backend service URL (default: http://backend:8000)
            AI_ANALYZER_URL: AI Analyzer URL (default: http://ai-analyzer:8001)

            # Redis
            REDIS_URL: Redis connection URL (default: redis://redis:6379/0)
            REDIS_ENABLED: Enable Redis (default: true)

            # Rate limiting
            RATE_LIMIT_RPM: Requests per minute (default: 100)
            RATE_LIMIT_BURST: Burst size (default: 20)
            RATE_LIMIT_PER_ORG: Enable per-org limiting (default: true)
            RATE_LIMIT_PER_IP: Enable per-IP limiting (default: true)
            RATE_LIMIT_BLOCK_DURATION: Block duration in seconds (default: 60)

            # Authentication
            REQUIRE_AUTHENTICATION: Require JWT auth (default: true)
            JWT_SECRET_KEY: JWT secret key
            JWT_ALGORITHM: JWT algorithm (default: HS256)

            # CORS
            CORS_ORIGINS: Comma-separated allowed origins (default: *)

            # Logging
            LOG_LEVEL: Logging level (default: INFO)
            LOG_REQUESTS: Log requests (default: true)

        Returns:
            GatewayConfig instance
        """
        # Rate limit config
        rate_limit = RateLimitConfig(
            requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "100")),
            burst_size=int(os.getenv("RATE_LIMIT_BURST", "20")),
            enable_per_organization=os.getenv("RATE_LIMIT_PER_ORG", "true").lower() == "true",
            enable_per_ip=os.getenv("RATE_LIMIT_PER_IP", "true").lower() == "true",
            block_duration_seconds=int(os.getenv("RATE_LIMIT_BLOCK_DURATION", "60")),
        )

        # CORS origins
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

        return cls(
            host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
            port=int(os.getenv("GATEWAY_PORT", "8000")),
            workers=int(os.getenv("GATEWAY_WORKERS", "4")),
            backend_url=os.getenv("BACKEND_URL", "http://backend:8000"),
            ai_analyzer_url=os.getenv("AI_ANALYZER_URL", "http://ai-analyzer:8001"),
            redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
            redis_enabled=os.getenv("REDIS_ENABLED", "true").lower() == "true",
            rate_limit=rate_limit,
            require_authentication=os.getenv("REQUIRE_AUTHENTICATION", "true").lower() == "true",
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            cors_origins=cors_origins,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_requests=os.getenv("LOG_REQUESTS", "true").lower() == "true",
        )


# Global configuration instance
_config: GatewayConfig = None


def get_config() -> GatewayConfig:
    """
    Get global configuration instance.

    Returns:
        GatewayConfig instance
    """
    global _config
    if _config is None:
        _config = GatewayConfig.from_env()
    return _config


def set_config(new_config: GatewayConfig):
    """
    Set global configuration instance.

    Args:
        new_config: New configuration
    """
    global _config
    _config = new_config
