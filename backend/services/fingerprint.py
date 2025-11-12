"""
Query fingerprinting and normalization utilities.

Converts SQL queries into normalized patterns by replacing literals
with placeholders, enabling grouping of similar queries.
"""
import re
import hashlib
from typing import Tuple

from core.logger import setup_logger

logger = setup_logger(__name__)


def normalize_query(sql: str) -> str:
    """
    Normalize a SQL query by replacing literal values with placeholders.

    This creates a "fingerprint" that represents the query pattern,
    allowing identical query structures to be grouped together.

    Examples:
        "SELECT * FROM users WHERE id = 123"
        -> "SELECT * FROM users WHERE id = ?"

        "SELECT * FROM orders WHERE status = 'PAID' AND price > 100"
        -> "SELECT * FROM orders WHERE status = ? AND price > ?"

    Args:
        sql: Original SQL query string

    Returns:
        Normalized SQL query with placeholders
    """
    # Handle bytes input from MySQL
    if isinstance(sql, bytes):
        sql = sql.decode('utf-8', errors='replace')

    if not sql:
        return ""

    # Remove extra whitespace and normalize spacing
    normalized = re.sub(r'\s+', ' ', sql.strip())

    # Replace string literals (single quotes)
    # Matches: 'string', 'string with spaces', 'string\'s with escapes'
    normalized = re.sub(r"'(?:[^'\\]|\\.)*'", "?", normalized)

    # Replace string literals (double quotes)
    normalized = re.sub(r'"(?:[^"\\\\]|\\\\.)*"', "?", normalized)

    # Replace numbers (integers and decimals)
    # Matches: 123, 123.45, -123, -123.45
    normalized = re.sub(r'\b-?\d+\.?\d*\b', '?', normalized)

    # Replace hex values (0x...)
    normalized = re.sub(r'\b0x[0-9a-fA-F]+\b', '?', normalized)

    # Normalize multiple consecutive placeholders
    # "WHERE x = ? AND y = ?" stays as is
    # "WHERE x IN (?, ?, ?)" -> "WHERE x IN (?)"
    normalized = re.sub(r'\(\s*\?\s*(?:,\s*\?\s*)+\)', '(?)', normalized)

    # Normalize LIMIT/OFFSET values
    normalized = re.sub(r'\bLIMIT\s+\?(?:\s+OFFSET\s+\?)?', 'LIMIT ?', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bOFFSET\s+\?', 'OFFSET ?', normalized, flags=re.IGNORECASE)

    # Remove trailing semicolon if present
    normalized = normalized.rstrip(';')

    return normalized


def generate_sql_hash(sql: str) -> str:
    """
    Generate a hash of the SQL query for deduplication.

    Uses MD5 hash of the fingerprint for fast lookups.

    Args:
        sql: SQL query string (can be original or fingerprint)

    Returns:
        Hex digest of the MD5 hash
    """
    if not sql:
        return ""

    return hashlib.md5(sql.encode('utf-8')).hexdigest()


def fingerprint_query(sql: str) -> Tuple[str, str]:
    """
    Generate both fingerprint and hash for a SQL query.

    This is the main function to use for query normalization.

    Args:
        sql: Original SQL query

    Returns:
        Tuple of (fingerprint, hash)

    Example:
        >>> fingerprint, hash = fingerprint_query("SELECT * FROM users WHERE id = 123")
        >>> print(fingerprint)
        "SELECT * FROM users WHERE id = ?"
        >>> print(hash)
        "abc123def456..."
    """
    fingerprint = normalize_query(sql)
    sql_hash = generate_sql_hash(fingerprint)

    return fingerprint, sql_hash


def extract_tables_from_query(sql: str) -> list[str]:
    """
    Extract table names mentioned in a SQL query.

    This is a simple heuristic-based extraction. For more accurate
    results, consider using a SQL parser library like sqlparse.

    Args:
        sql: SQL query string

    Returns:
        List of table names found in the query
    """
    tables = []

    # Normalize query
    sql_lower = sql.lower()

    # Pattern to match FROM and JOIN clauses
    # Simplified: looks for FROM/JOIN followed by word characters
    patterns = [
        r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, sql_lower)
        tables.extend(matches)

    # Remove duplicates while preserving order
    seen = set()
    unique_tables = []
    for table in tables:
        if table not in seen:
            seen.add(table)
            unique_tables.append(table)

    return unique_tables


def classify_query_type(sql: str) -> str:
    """
    Classify the type of SQL query.

    Args:
        sql: SQL query string (or bytes, will be decoded)

    Returns:
        Query type: SELECT, INSERT, UPDATE, DELETE, or OTHER
    """
    # Handle bytes input from MySQL
    if isinstance(sql, bytes):
        sql = sql.decode('utf-8', errors='replace')

    sql_upper = sql.strip().upper()

    if sql_upper.startswith('SELECT'):
        return 'SELECT'
    elif sql_upper.startswith('INSERT'):
        return 'INSERT'
    elif sql_upper.startswith('UPDATE'):
        return 'UPDATE'
    elif sql_upper.startswith('DELETE'):
        return 'DELETE'
    elif sql_upper.startswith('CREATE'):
        return 'CREATE'
    elif sql_upper.startswith('ALTER'):
        return 'ALTER'
    elif sql_upper.startswith('DROP'):
        return 'DROP'
    else:
        return 'OTHER'


def is_query_safe_to_explain(sql: str) -> bool:
    """
    Check if a query is safe to run EXPLAIN on.

    EXPLAIN should only be run on SELECT queries. Running it on
    INSERT/UPDATE/DELETE could have side effects.

    Args:
        sql: SQL query string

    Returns:
        True if safe to EXPLAIN, False otherwise
    """
    query_type = classify_query_type(sql)
    return query_type == 'SELECT'


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_queries = [
        "SELECT * FROM users WHERE id = 123",
        "SELECT * FROM orders WHERE status = 'PAID' AND price > 100.50",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE u.country = 'IT'",
        "INSERT INTO logs VALUES (1, 'test', NOW())",
        "UPDATE users SET name = 'John' WHERE id = 456",
    ]

    print("Query Fingerprinting Test\n" + "="*60)

    for sql in test_queries:
        fingerprint, sql_hash = fingerprint_query(sql)
        query_type = classify_query_type(sql)
        tables = extract_tables_from_query(sql)
        safe_to_explain = is_query_safe_to_explain(sql)

        print(f"\nOriginal:   {sql}")
        print(f"Fingerprint: {fingerprint}")
        print(f"Hash:        {sql_hash[:16]}...")
        print(f"Type:        {query_type}")
        print(f"Tables:      {', '.join(tables)}")
        print(f"Safe EXPLAIN: {safe_to_explain}")
