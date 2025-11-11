"""
Base collector for database slow query collection.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class SlowQuery:
    """Slow query data structure."""
    sql_text: str
    sql_fingerprint: str
    query_time: float
    lock_time: float = 0.0
    rows_sent: int = 0
    rows_examined: int = 0
    database_name: Optional[str] = None
    user_host: Optional[str] = None
    start_time: Optional[datetime] = None
    collected_at: datetime = None

    def __post_init__(self):
        """Set defaults after initialization."""
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()

        if not self.sql_fingerprint:
            self.sql_fingerprint = self._generate_fingerprint(self.sql_text)

    @staticmethod
    def _generate_fingerprint(sql: str) -> str:
        """
        Generate a fingerprint (hash) for the SQL query.

        Args:
            sql: SQL query text

        Returns:
            MD5 hash of the normalized SQL
        """
        # Normalize SQL for fingerprinting
        normalized = sql.strip().upper()

        # Remove multiple spaces
        normalized = ' '.join(normalized.split())

        # Generate MD5 hash
        return hashlib.md5(normalized.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API transmission."""
        return {
            'sql_text': self.sql_text,
            'sql_fingerprint': self.sql_fingerprint,
            'query_time': self.query_time,
            'lock_time': self.lock_time,
            'rows_sent': self.rows_sent,
            'rows_examined': self.rows_examined,
            'database_name': self.database_name,
            'user_host': self.user_host,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
        }


class BaseCollector(ABC):
    """
    Abstract base class for database collectors.

    Each database type (MySQL, PostgreSQL, etc.) should implement this interface.
    """

    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize collector.

        Args:
            connection_config: Database connection configuration
        """
        self.config = connection_config
        self.connection = None

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the database.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from the database."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to database.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def collect_slow_queries(
        self,
        threshold: float = 1.0,
        limit: int = 100
    ) -> List[SlowQuery]:
        """
        Collect slow queries from the database.

        Args:
            threshold: Minimum query time in seconds
            limit: Maximum number of queries to collect

        Returns:
            List of SlowQuery objects
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection is working, False otherwise
        """
        pass

    @abstractmethod
    def get_database_version(self) -> Optional[str]:
        """
        Get database version string.

        Returns:
            Database version or None if unavailable
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on collector.

        Returns:
            Dictionary with health check results
        """
        result = {
            'collector_type': self.__class__.__name__,
            'connected': False,
            'database': self.config.get('database'),
            'host': self.config.get('host'),
            'error': None
        }

        try:
            result['connected'] = self.is_connected()
            if result['connected']:
                result['version'] = self.get_database_version()
        except Exception as e:
            result['error'] = str(e)

        return result

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
