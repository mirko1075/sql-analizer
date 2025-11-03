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
    mysql_db: str = os.getenv("MYSQL_DB", "labdb")
    
    # AI Configuration
    ai_base_url: str = os.getenv("AI_BASE_URL", "http://ai-llama:11434")
    ai_model: str = os.getenv("AI_MODEL", "llama3.1:8b")
    
    # Application Settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    collection_interval: int = int(os.getenv("COLLECTION_INTERVAL", "60"))
    
    def get_mysql_connection_string(self) -> str:
        """Get MySQL connection string for SQLAlchemy."""
        return f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    def get_mysql_dict(self) -> dict:
        """Get MySQL connection parameters as dictionary."""
        return {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.mysql_db
        }


# Global settings instance
settings = Settings()
