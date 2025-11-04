"""
Configuration management for DBPower Base.
Loads settings from environment variables.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """
    Application settings loaded from environment variables.
    Single point of configuration for the entire application.
    """
    
    # MySQL Database to Monitor
    mysql_host: str = os.getenv("MYSQL_HOST", "mysql-lab")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "root")
    mysql_db: str = os.getenv("MYSQL_DB", "")  # Empty = monitor all databases
    mysql_database: str = os.getenv("MYSQL_DB", "")  # Alias for compatibility
    
    # DBPower Monitoring User (to filter out from slow queries)
    dbpower_user: str = os.getenv("DBPOWER_USER", "dbpower_monitor")
    dbpower_password: str = os.getenv("DBPOWER_PASSWORD", "dbpower_secure_pass")
    
    # AI Configuration - Provider Selection
    ai_provider: str = os.getenv("AI_PROVIDER", "llama").lower()  # llama, openai, anthropic
    ai_log_requests: bool = os.getenv("AI_LOG_REQUESTS", "true").lower() == "true"
    ai_timeout: float = float(os.getenv("AI_TIMEOUT", "120.0"))
    ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "3"))
    
    # LLaMA/Ollama Configuration (local)
    llama_base_url: str = os.getenv("LLAMA_BASE_URL", "http://ai-llama:11434")
    llama_model: str = os.getenv("LLAMA_MODEL", "llama3.1:8b")
    
    # OpenAI Configuration (cloud)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    
    # Anthropic Configuration (cloud)
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
    anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    anthropic_max_tokens: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2000"))
    
    # Legacy AI Configuration (backward compatibility)
    ai_base_url: str = os.getenv("AI_BASE_URL", "http://ai-llama:11434")
    ai_model: str = os.getenv("AI_MODEL", "llama3.1:8b")
    
    # Application Settings
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    collection_interval: int = int(os.getenv("COLLECTION_INTERVAL", "60"))
    
    def get_mysql_connection_string(self) -> str:
        """Get MySQL connection string for SQLAlchemy."""
        return f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    def get_mysql_dict(self) -> dict:
        """Get MySQL connection parameters as dictionary."""
        params = {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
        }
        # Only add database if specified
        if self.mysql_db:
            params["database"] = self.mysql_db
        return params


# Global settings instance
settings = Settings()
