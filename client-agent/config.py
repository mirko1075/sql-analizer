"""
Client Agent Configuration.
Manages connection to customer databases and SaaS backend.
"""
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MARIADB = "mariadb"


class AnonymizationLevel(str, Enum):
    """Data anonymization levels."""
    STRICT = "strict"      # Mask all values, only structure
    MODERATE = "moderate"  # Mask sensitive data (emails, IPs, etc.)
    MINIMAL = "minimal"    # Only mask obvious PII


@dataclass
class DatabaseConnection:
    """Database connection configuration."""
    id: str
    type: DatabaseType
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl: bool = False
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None

    # Collection settings
    collection_interval: int = 60  # seconds
    slow_query_threshold: float = 1.0  # seconds

    # Metadata
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    identity_id: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConnection':
        """Create from dictionary."""
        db_type = DatabaseType(data.get('type', 'mysql').lower())
        return cls(
            id=data['id'],
            type=db_type,
            host=data['host'],
            port=int(data.get('port', 3306 if db_type == DatabaseType.MYSQL else 5432)),
            database=data['database'],
            user=data['user'],
            password=data['password'],
            ssl=data.get('ssl', False),
            ssl_ca=data.get('ssl_ca'),
            ssl_cert=data.get('ssl_cert'),
            ssl_key=data.get('ssl_key'),
            collection_interval=int(data.get('collection_interval', 60)),
            slow_query_threshold=float(data.get('slow_query_threshold', 1.0)),
            organization_id=data.get('organization_id'),
            team_id=data.get('team_id'),
            identity_id=data.get('identity_id'),
        )


@dataclass
class SaaSConfig:
    """SaaS backend configuration."""
    api_url: str
    api_key: str
    verify_ssl: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds

    @classmethod
    def from_env(cls) -> 'SaaSConfig':
        """Load from environment variables."""
        return cls(
            api_url=os.getenv('SAAS_API_URL', 'https://api.dbpower.cloud/api/v1'),
            api_key=os.getenv('SAAS_API_KEY', ''),
            verify_ssl=os.getenv('SAAS_VERIFY_SSL', 'true').lower() == 'true',
            timeout=int(os.getenv('SAAS_TIMEOUT', '30')),
            retry_attempts=int(os.getenv('SAAS_RETRY_ATTEMPTS', '3')),
            retry_delay=int(os.getenv('SAAS_RETRY_DELAY', '5')),
        )


@dataclass
class ClientAgentConfig:
    """Main client agent configuration."""
    agent_id: str
    databases: List[DatabaseConnection]
    saas: SaaSConfig
    anonymization_level: AnonymizationLevel = AnonymizationLevel.STRICT
    log_level: str = "INFO"

    # Health check settings
    health_check_interval: int = 300  # seconds (5 minutes)
    health_check_port: int = 8080

    # Storage (local cache before sending)
    cache_dir: str = "/var/lib/dbpower-agent/cache"
    max_cache_size_mb: int = 100

    @classmethod
    def from_env(cls) -> 'ClientAgentConfig':
        """Load configuration from environment variables."""
        # Agent ID
        agent_id = os.getenv('CLIENT_AGENT_ID')
        if not agent_id:
            raise ValueError("CLIENT_AGENT_ID environment variable is required")

        # Database connections from JSON
        db_connections_json = os.getenv('DB_CONNECTIONS', '[]')
        try:
            db_configs = json.loads(db_connections_json)
            databases = [DatabaseConnection.from_dict(db) for db in db_configs]
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid DB_CONNECTIONS JSON: {e}")

        if not databases:
            raise ValueError("At least one database connection is required")

        # SaaS configuration
        saas = SaaSConfig.from_env()
        if not saas.api_key:
            raise ValueError("SAAS_API_KEY environment variable is required")

        # Anonymization level
        anon_level_str = os.getenv('ANONYMIZATION_LEVEL', 'strict').lower()
        try:
            anonymization_level = AnonymizationLevel(anon_level_str)
        except ValueError:
            raise ValueError(f"Invalid ANONYMIZATION_LEVEL: {anon_level_str}")

        return cls(
            agent_id=agent_id,
            databases=databases,
            saas=saas,
            anonymization_level=anonymization_level,
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '300')),
            health_check_port=int(os.getenv('HEALTH_CHECK_PORT', '8080')),
            cache_dir=os.getenv('CACHE_DIR', '/var/lib/dbpower-agent/cache'),
            max_cache_size_mb=int(os.getenv('MAX_CACHE_SIZE_MB', '100')),
        )

    @classmethod
    def from_file(cls, config_file: str) -> 'ClientAgentConfig':
        """Load configuration from JSON file."""
        with open(config_file, 'r') as f:
            data = json.load(f)

        databases = [DatabaseConnection.from_dict(db) for db in data.get('databases', [])]

        saas_data = data.get('saas', {})
        saas = SaaSConfig(
            api_url=saas_data.get('api_url', 'https://api.dbpower.cloud/api/v1'),
            api_key=saas_data['api_key'],
            verify_ssl=saas_data.get('verify_ssl', True),
            timeout=saas_data.get('timeout', 30),
            retry_attempts=saas_data.get('retry_attempts', 3),
            retry_delay=saas_data.get('retry_delay', 5),
        )

        return cls(
            agent_id=data['agent_id'],
            databases=databases,
            saas=saas,
            anonymization_level=AnonymizationLevel(data.get('anonymization_level', 'strict')),
            log_level=data.get('log_level', 'INFO'),
            health_check_interval=data.get('health_check_interval', 300),
            health_check_port=data.get('health_check_port', 8080),
            cache_dir=data.get('cache_dir', '/var/lib/dbpower-agent/cache'),
            max_cache_size_mb=data.get('max_cache_size_mb', 100),
        )

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate agent ID
        if not self.agent_id or len(self.agent_id) < 3:
            errors.append("agent_id must be at least 3 characters")

        # Validate databases
        if not self.databases:
            errors.append("At least one database connection is required")

        for i, db in enumerate(self.databases):
            if not db.host:
                errors.append(f"Database {i}: host is required")
            if not db.database:
                errors.append(f"Database {i}: database name is required")
            if not db.user:
                errors.append(f"Database {i}: user is required")
            if not db.password:
                errors.append(f"Database {i}: password is required")
            if db.port <= 0 or db.port > 65535:
                errors.append(f"Database {i}: invalid port {db.port}")

        # Validate SaaS
        if not self.saas.api_url:
            errors.append("SaaS API URL is required")
        if not self.saas.api_key:
            errors.append("SaaS API key is required")
        if not self.saas.api_key.startswith('dbp_'):
            errors.append("SaaS API key must start with 'dbp_'")

        return errors
