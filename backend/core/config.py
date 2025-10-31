"""
Configuration management for AI Query Analyzer backend.

Loads and validates configuration from environment variables.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for a database connection."""
    host: str
    port: int
    user: str
    password: str
    database: str

    def get_connection_string(self, db_type: str = 'postgresql') -> str:
        """Generate database connection string."""
        if db_type == 'postgresql':
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif db_type == 'mysql':
            return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (useful for logging without password)."""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'database': self.database,
            # Exclude password for security
        }


@dataclass
class Settings:
    """
    Application settings loaded from environment variables.

    All database configurations and application settings are centralized here.
    """

    # Application settings
    env: str = field(default_factory=lambda: os.getenv('ENV', 'development'))
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')

    # Internal database (PostgreSQL for storing collected queries and analysis)
    internal_db: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        host=os.getenv('INTERNAL_DB_HOST', 'localhost'),
        port=int(os.getenv('INTERNAL_DB_PORT', '5440')),
        user=os.getenv('INTERNAL_DB_USER', 'ai_core'),
        password=os.getenv('INTERNAL_DB_PASSWORD', 'ai_core'),
        database=os.getenv('INTERNAL_DB_NAME', 'ai_core'),
    ))

    # Redis configuration
    redis_host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    redis_port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    redis_db: int = field(default_factory=lambda: int(os.getenv('REDIS_DB', '0')))

    # Lab MySQL database (target for slow query collection)
    mysql_lab: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', '3307')),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'root'),
        database=os.getenv('MYSQL_DB', 'labdb'),
    ))

    # Lab PostgreSQL database (target for slow query collection)
    postgres_lab: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        host=os.getenv('PG_HOST', '127.0.0.1'),
        port=int(os.getenv('PG_PORT', '5433')),
        user=os.getenv('PG_USER', 'postgres'),
        password=os.getenv('PG_PASSWORD', 'root'),
        database=os.getenv('PG_DB', 'labdb'),
    ))

    # Collector settings
    collector_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv('COLLECTOR_INTERVAL', '300'))
    )  # Run collector every 5 minutes by default

    # Analyzer settings
    analyzer_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv('ANALYZER_INTERVAL', '600'))
    )  # Run analyzer every 10 minutes by default

    # AI provider settings (abstract interface, no hardcoded provider)
    ai_provider: str = field(default_factory=lambda: os.getenv('AI_PROVIDER', 'stub'))
    ai_api_key: Optional[str] = field(default_factory=lambda: os.getenv('AI_API_KEY'))
    ai_model: str = field(default_factory=lambda: os.getenv('AI_MODEL', 'gpt-4'))

    # API settings
    api_title: str = "AI Query Analyzer API"
    api_version: str = "1.0.0"
    api_description: str = "API for collecting, analyzing, and optimizing slow SQL queries"

    def __post_init__(self):
        """Validate configuration after initialization."""
        logger.info("Configuration loaded:")
        logger.info(f"  Environment: {self.env}")
        logger.info(f"  Log Level: {self.log_level}")
        logger.info(f"  Internal DB: {self.internal_db.to_dict()}")
        logger.info(f"  MySQL Lab: {self.mysql_lab.to_dict()}")
        logger.info(f"  PostgreSQL Lab: {self.postgres_lab.to_dict()}")
        logger.info(f"  Redis: {self.redis_host}:{self.redis_port}")
        logger.info(f"  Collector Interval: {self.collector_interval_seconds}s")
        logger.info(f"  Analyzer Interval: {self.analyzer_interval_seconds}s")
        logger.info(f"  AI Provider: {self.ai_provider}")

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings instance
    """
    return settings


def reload_settings():
    """
    Reload settings from environment variables.

    Useful for testing or dynamic configuration changes.
    """
    global settings
    settings = Settings()
    logger.info("Settings reloaded")


# Validate critical settings on import
if __name__ != "__main__":
    # Check that at least one target database is configured
    if not settings.mysql_lab.host and not settings.postgres_lab.host:
        logger.warning("No target databases configured for slow query collection")
