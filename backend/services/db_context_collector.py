"""
Database context collector.

Gathers table schema, index metadata, statistics, and configuration details
for both MySQL and PostgreSQL targets so AI analyses can reason with full context.
"""
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
import psycopg2
from mysql.connector import Error as MySQLError
from psycopg2 import OperationalError as PsycopgOperationalError

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.models import DbMetadataCache
from backend.db.session import get_db_context

logger = get_logger(__name__)

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _sanitize_identifier(identifier: str) -> Optional[str]:
    """
    Ensure identifiers are safe to interpolate into SQL.

    Returns sanitized identifier or None if invalid.
    """
    if not identifier:
        return None
    if IDENTIFIER_RE.match(identifier):
        return identifier
    logger.warning("Skipping unsupported identifier: %s", identifier)
    return None


def _normalize_table_reference(raw: str) -> Optional[str]:
    """
    Normalise table references coming from fingerprints/queries.

    Handles aliases (e.g. "users u"), schema prefixes ("public.users"),
    and quoted identifiers (`users`, "Users").
    """
    if not raw:
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    # Remove trailing alias (split at first whitespace)
    candidate = candidate.split()[0]

    # Strip quoting characters
    candidate = candidate.strip('`"')

    # Remove schema qualification
    if "." in candidate:
        candidate = candidate.split(".")[-1]

    # Final sanitization
    return _sanitize_identifier(candidate)


def _prepare_table_list(tables: List[str]) -> List[str]:
    """
    Normalize and deduplicate table references.
    """
    seen = {}
    for table in tables:
        normalized = _normalize_table_reference(table)
        if normalized:
            seen[normalized] = True
    return list(seen.keys())


@contextmanager
def _mysql_connection():
    """Context manager for MySQL connections."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=settings.mysql_lab.host,
            port=settings.mysql_lab.port,
            user=settings.mysql_lab.user,
            password=settings.mysql_lab.password,
            database=settings.mysql_lab.database,
        )
        yield conn
    finally:
        if conn and conn.is_connected():
            conn.close()


@contextmanager
def _postgres_connection():
    """Context manager for PostgreSQL connections."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.postgres_lab.host,
            port=settings.postgres_lab.port,
            user=settings.postgres_lab.user,
            password=settings.postgres_lab.password,
            dbname=settings.postgres_lab.database,
        )
        yield conn
    finally:
        if conn:
            conn.close()


class DatabaseContextCollector:
    """
    Collects metadata, statistics, and configuration for target databases.

    Results are persisted in db_metadata_cache with a default TTL of one hour.
    """

    CACHE_TTL_SECONDS = 3600

    def __init__(self, ttl_seconds: Optional[int] = None):
        self.ttl_seconds = ttl_seconds or self.CACHE_TTL_SECONDS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_context(self, db_type: str, tables: List[str]) -> Dict[str, Any]:
        """
        Retrieve metadata context for given tables.

        Args:
            db_type: "mysql" or "postgres"
            tables: List of table names involved in the query
        """
        db_type = db_type.lower()
        sanitized_tables = _prepare_table_list(tables)

        if not sanitized_tables:
            logger.info("No valid tables requested for context collection")
            sanitized_tables = []

        if db_type == "mysql":
            return self.get_mysql_context(sanitized_tables)
        if db_type in {"postgres", "postgresql"}:
            return self.get_postgres_context(sanitized_tables)

        raise ValueError(f"Unsupported database type for context collector: {db_type}")

    def get_mysql_context(self, query_tables: List[str]) -> Dict[str, Any]:
        """Collect metadata for MySQL tables."""
        host = settings.mysql_lab.host
        db_name = settings.mysql_lab.database

        cached_payload, cache_entry = self._load_cache("mysql", host, db_name)
        if cached_payload and self._cache_is_valid(cache_entry, query_tables):
            return self._subset_payload(cached_payload, query_tables)

        try:
            with _mysql_connection() as conn:
                if not conn or not conn.is_connected():
                    raise ConnectionError("Unable to connect to MySQL lab database")

                payload = self._collect_mysql_metadata(conn, query_tables)
        except MySQLError as exc:
            logger.error("MySQL metadata collection failed: %s", exc)
            if cached_payload:
                logger.info("Falling back to stale cache for MySQL metadata")
                return self._subset_payload(cached_payload, query_tables)
            raise

        self._upsert_cache("mysql", host, db_name, payload, cache_entry)
        return self._subset_payload(payload, query_tables)

    def get_postgres_context(self, query_tables: List[str]) -> Dict[str, Any]:
        """Collect metadata for PostgreSQL tables."""
        host = settings.postgres_lab.host
        db_name = settings.postgres_lab.database

        cached_payload, cache_entry = self._load_cache("postgres", host, db_name)
        if cached_payload and self._cache_is_valid(cache_entry, query_tables):
            return self._subset_payload(cached_payload, query_tables)

        try:
            with _postgres_connection() as conn:
                payload = self._collect_postgres_metadata(conn, query_tables)
        except PsycopgOperationalError as exc:
            logger.error("PostgreSQL metadata collection failed: %s", exc)
            if cached_payload:
                logger.info("Falling back to stale cache for PostgreSQL metadata")
                return self._subset_payload(cached_payload, query_tables)
            raise

        self._upsert_cache("postgres", host, db_name, payload, cache_entry)
        return self._subset_payload(payload, query_tables)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def _load_cache(
        self,
        db_type: str,
        host: str,
        database: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[DbMetadataCache]]:
        with get_db_context() as db:
            entry = db.query(DbMetadataCache).filter(
                DbMetadataCache.source_db_type == db_type,
                DbMetadataCache.source_db_host == host,
                DbMetadataCache.source_db_name == database,
            ).first()

            if not entry:
                return None, None

            payload = {
                "tables": entry.tables or {},
                "indexes": entry.indexes or {},
                "statistics": entry.statistics or {},
                "configuration": entry.configuration or {},
                "relations": entry.relations or {},
                "collected_at": entry.collected_at.isoformat() if entry.collected_at is not None else None,
            }
            return payload, entry

    def _cache_is_valid(self, entry: Optional[DbMetadataCache], tables: List[str]) -> bool:
        if not entry:
            return False
        if getattr(entry, "expires_at", None) is not None and getattr(entry, "expires_at", datetime.utcnow()) < datetime.utcnow():
            return False

        # Ensure cache has coverage for requested tables
        cached_tables = set((entry.tables or {}).keys())
        missing = {tbl for tbl in tables if tbl not in cached_tables}
        if missing:
            logger.info("Metadata cache missing tables: %s", ", ".join(sorted(missing)))
            return False

        return True

    def _upsert_cache(
        self,
        db_type: str,
        host: str,
        database: str,
        payload: Dict[str, Any],
        entry: Optional[DbMetadataCache],
    ) -> None:
        expiry = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

        with get_db_context() as db:
            if entry:
                entry.tables = payload.get("tables")
                entry.indexes = payload.get("indexes")
                entry.statistics = payload.get("statistics")
                entry.configuration = payload.get("configuration")
                entry.relations = payload.get("relations")
                entry.collected_at = datetime.utcnow()
                entry.expires_at = expiry
            else:
                entry = DbMetadataCache(
                    source_db_type=db_type,
                    source_db_host=host,
                    source_db_name=database,
                    tables=payload.get("tables"),
                    indexes=payload.get("indexes"),
                    statistics=payload.get("statistics"),
                    configuration=payload.get("configuration"),
                    relations=payload.get("relations"),
                    collected_at=datetime.utcnow(),
                    expires_at=expiry,
                )
                db.add(entry)
            db.commit()

    def _subset_payload(self, payload: Dict[str, Any], tables: List[str]) -> Dict[str, Any]:
        """Return payload containing only requested tables (if provided)."""
        if not tables:
            return payload

        subset = payload.copy()
        subset["tables"] = {t: payload.get("tables", {}).get(t) for t in tables if t in payload.get("tables", {})}
        subset["indexes"] = {t: payload.get("indexes", {}).get(t) for t in tables if t in payload.get("indexes", {})}
        subset["statistics"] = {t: payload.get("statistics", {}).get(t) for t in tables if t in payload.get("statistics", {})}
        subset["relations"] = payload.get("relations", {})
        subset["configuration"] = payload.get("configuration")
        return subset

    # ------------------------------------------------------------------
    # MySQL metadata collectors
    # ------------------------------------------------------------------
    def _collect_mysql_metadata(self, conn, query_tables: List[str]) -> Dict[str, Any]:
        cursor = conn.cursor(dictionary=True)
        tables = query_tables or self._list_mysql_tables(cursor)
        table_metadata = {}
        index_metadata = {}
        stats_metadata = {}
        relations = {}

        for table in tables:
            sanitized = _sanitize_identifier(table)
            if not sanitized:
                continue

            table_metadata[sanitized] = self._mysql_table_schema(cursor, sanitized)
            index_metadata[sanitized] = self._mysql_index_info(cursor, sanitized)
            stats_metadata[sanitized] = self._mysql_table_stats(cursor, sanitized)
            relations[sanitized] = self._mysql_table_relations(cursor, sanitized)

        configuration = self._mysql_configuration(cursor)
        cursor.close()

        return {
            "tables": table_metadata,
            "indexes": index_metadata,
            "statistics": stats_metadata,
            "relations": relations,
            "configuration": configuration,
            "collected_at": datetime.utcnow().isoformat(),
        }

    def _list_mysql_tables(self, cursor) -> List[str]:
        cursor.execute("SHOW TABLES")
        rows = cursor.fetchall()
        return [list(row.values())[0] for row in rows]

    def _mysql_table_schema(self, cursor, table: str) -> List[Dict[str, Any]]:
        cursor.execute(f"SHOW FULL COLUMNS FROM `{table}`")
        columns = cursor.fetchall()
        return [
            {
                "column": col.get("Field"),
                "type": col.get("Type"),
                "nullable": col.get("Null") == "YES",
                "default": col.get("Default"),
                "extra": col.get("Extra"),
                "collation": col.get("Collation"),
                "comment": col.get("Comment"),
            }
            for col in columns
        ]

    def _mysql_index_info(self, cursor, table: str) -> List[Dict[str, Any]]:
        cursor.execute(f"SHOW INDEX FROM `{table}`")
        rows = cursor.fetchall()
        indexes = {}
        for row in rows:
            key_name = row.get("Key_name")
            entry = indexes.setdefault(
                key_name,
                {
                    "name": key_name,
                    "unique": not bool(row.get("Non_unique")),
                    "type": row.get("Index_type"),
                    "columns": [],
                },
            )
            entry["columns"].append({
                "column": row.get("Column_name"),
                "order": row.get("Seq_in_index"),
                "sub_part": row.get("Sub_part"),
            })
        return list(indexes.values())

    def _mysql_table_stats(self, cursor, table: str) -> Dict[str, Any]:
        cursor.execute(f"SHOW TABLE STATUS LIKE %s", (table,))
        row = cursor.fetchone()
        if not row:
            return {}
        return {
            "engine": row.get("Engine"),
            "rows": row.get("Rows"),
            "avg_row_length": row.get("Avg_row_length"),
            "data_length": row.get("Data_length"),
            "index_length": row.get("Index_length"),
            "data_free": row.get("Data_free"),
            "auto_increment": row.get("Auto_increment"),
            "create_time": row.get("Create_time").isoformat() if row.get("Create_time") else None,
            "update_time": row.get("Update_time").isoformat() if row.get("Update_time") else None,
        }

    def _mysql_table_relations(self, cursor, table: str) -> Dict[str, Any]:
        query = """
            SELECT
                constraint_name,
                referenced_table_name,
                GROUP_CONCAT(column_name ORDER BY ordinal_position) AS columns,
                GROUP_CONCAT(referenced_column_name ORDER BY position_in_unique_constraint) AS referenced_columns
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
              AND table_name = %s
              AND referenced_table_name IS NOT NULL
            GROUP BY constraint_name, referenced_table_name
        """
        cursor.execute(query, (settings.mysql_lab.database, table))
        relations = cursor.fetchall()
        return [
            {
                "constraint": rel.get("constraint_name"),
                "referenced_table": rel.get("referenced_table_name"),
                "columns": (rel.get("columns") or "").split(","),
                "referenced_columns": (rel.get("referenced_columns") or "").split(","),
            }
            for rel in relations
        ]

    def _mysql_configuration(self, cursor) -> Dict[str, Any]:
        interesting = [
            "innodb_buffer_pool_size",
            "query_cache_size",
            "tmp_table_size",
            "max_heap_table_size",
            "innodb_log_file_size",
        ]
        format_strings = ",".join(["%s"] * len(interesting))
        cursor.execute(
            f"SHOW VARIABLES WHERE Variable_name IN ({format_strings})",
            interesting,
        )
        rows = cursor.fetchall()
        return {row["Variable_name"]: row["Value"] for row in rows}

    # ------------------------------------------------------------------
    # PostgreSQL metadata collectors
    # ------------------------------------------------------------------
    def _collect_postgres_metadata(self, conn, query_tables: List[str]) -> Dict[str, Any]:
        cursor = conn.cursor()
        tables = query_tables or self._list_postgres_tables(cursor)
        table_metadata = {}
        index_metadata = {}
        stats_metadata = {}
        relations = {}

        for table in tables:
            sanitized = _sanitize_identifier(table)
            if not sanitized:
                continue

            table_metadata[sanitized] = self._postgres_table_schema(cursor, sanitized)
            index_metadata[sanitized] = self._postgres_index_info(cursor, sanitized)
            stats_metadata[sanitized] = self._postgres_table_stats(cursor, sanitized)
            relations[sanitized] = self._postgres_table_relations(cursor, sanitized)

        configuration = self._postgres_configuration(cursor)
        cursor.close()

        return {
            "tables": table_metadata,
            "indexes": index_metadata,
            "statistics": stats_metadata,
            "relations": relations,
            "configuration": configuration,
            "collected_at": datetime.utcnow().isoformat(),
        }

    def _list_postgres_tables(self, cursor) -> List[str]:
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """)
        return [row[0] for row in cursor.fetchall()]

    def _postgres_table_schema(self, cursor, table: str) -> List[Dict[str, Any]]:
        cursor.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = cursor.fetchall()
        return [
            {
                "column": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
            }
            for row in rows
        ]

    def _postgres_index_info(self, cursor, table: str) -> List[Dict[str, Any]]:
        cursor.execute(
            """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = %s
            """,
            (table,),
        )
        rows = cursor.fetchall()
        indexes = []
        for row in rows:
            indexes.append(
                {
                    "name": row[0],
                    "definition": row[1],
                }
            )
        return indexes

    def _postgres_table_stats(self, cursor, table: str) -> Dict[str, Any]:
        cursor.execute(
            """
            SELECT
                reltuples::bigint AS estimated_rows,
                pg_total_relation_size(relid) AS total_size,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
              AND relname = %s
            """,
            (table,),
        )
        row = cursor.fetchone()
        if not row:
            return {}
        return {
            "estimated_rows": row[0],
            "total_size": row[1],
            "seq_scan": row[2],
            "seq_tup_read": row[3],
            "idx_scan": row[4],
            "idx_tup_fetch": row[5],
        }

    def _postgres_table_relations(self, cursor, table: str) -> List[Dict[str, Any]]:
        cursor.execute(
            """
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
            """,
            (table,),
        )
        rows = cursor.fetchall()
        rels: Dict[str, Dict[str, Any]] = {}
        for constraint, column, foreign_table, foreign_column in rows:
            entry = rels.setdefault(
                constraint,
                {
                    "constraint": constraint,
                    "referenced_table": foreign_table,
                    "columns": [],
                    "referenced_columns": [],
                },
            )
            entry["columns"].append(column)
            entry["referenced_columns"].append(foreign_column)
        return list(rels.values())

    def _postgres_configuration(self, cursor) -> Dict[str, Any]:
        interesting = [
            "shared_buffers",
            "work_mem",
            "maintenance_work_mem",
            "effective_cache_size",
            "random_page_cost",
        ]
        cursor.execute(
            """
            SELECT name, setting
            FROM pg_settings
            WHERE name = ANY(%s)
            """,
            (interesting,),
        )
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
