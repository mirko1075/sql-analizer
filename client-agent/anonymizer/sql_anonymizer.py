"""
SQL Anonymization Engine.
Masks sensitive data in SQL queries before sending to SaaS backend.
"""
import re
from typing import Dict, List, Tuple
from enum import Enum


class AnonymizationLevel(str, Enum):
    """Data anonymization levels."""
    STRICT = "strict"      # Mask all values
    MODERATE = "moderate"  # Mask sensitive data only
    MINIMAL = "minimal"    # Only mask obvious PII


class SQLAnonymizer:
    """
    Anonymizes SQL queries by masking sensitive data.

    Supports different anonymization levels and handles:
    - String literals
    - Numeric values
    - Email addresses
    - IP addresses
    - Credit card numbers
    - Phone numbers
    - Dates and timestamps
    """

    def __init__(self, level: AnonymizationLevel = AnonymizationLevel.STRICT):
        """
        Initialize anonymizer.

        Args:
            level: Anonymization level (strict, moderate, minimal)
        """
        self.level = level

        # Regex patterns for sensitive data
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'date': re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
            'datetime': re.compile(r'\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\b'),
        }

    def anonymize(self, sql: str) -> Tuple[str, Dict[str, int]]:
        """
        Anonymize SQL query.

        Args:
            sql: Original SQL query

        Returns:
            Tuple of (anonymized_sql, stats)
            stats contains count of each type of anonymization
        """
        stats = {
            'strings': 0,
            'numbers': 0,
            'emails': 0,
            'ip_addresses': 0,
            'credit_cards': 0,
            'phones': 0,
            'ssns': 0,
            'dates': 0,
        }

        anonymized = sql

        if self.level == AnonymizationLevel.STRICT:
            anonymized, stats = self._anonymize_strict(anonymized, stats)
        elif self.level == AnonymizationLevel.MODERATE:
            anonymized, stats = self._anonymize_moderate(anonymized, stats)
        else:  # MINIMAL
            anonymized, stats = self._anonymize_minimal(anonymized, stats)

        return anonymized, stats

    def _anonymize_strict(self, sql: str, stats: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
        """
        Strict anonymization: mask all values.

        Args:
            sql: SQL query
            stats: Statistics dictionary

        Returns:
            Tuple of (anonymized_sql, updated_stats)
        """
        result = sql

        # Mask all string literals (single and double quotes)
        # Match strings but avoid SQL keywords
        string_pattern = re.compile(r"'([^']*)'")
        matches = list(string_pattern.finditer(result))
        for match in reversed(matches):
            content = match.group(1)
            # Skip if it's a SQL keyword or empty
            if content and not self._is_sql_keyword(content):
                # Check for sensitive patterns inside the string
                masked_content, pattern_type = self._mask_string_content(content)
                result = result[:match.start()] + f"'{masked_content}'" + result[match.end():]
                if pattern_type == 'email':
                    stats['emails'] += 1
                elif pattern_type == 'credit_card':
                    stats['credit_cards'] += 1
                elif pattern_type == 'ip_address':
                    stats['ip_addresses'] += 1
                elif pattern_type == 'phone':
                    stats['phones'] += 1
                elif pattern_type == 'ssn':
                    stats['ssns'] += 1
                else:
                    stats['strings'] += 1

        # Mask double-quoted strings
        double_quote_pattern = re.compile(r'"([^"]*)"')
        matches = list(double_quote_pattern.finditer(result))
        for match in reversed(matches):
            content = match.group(1)
            if content and not self._is_sql_keyword(content):
                masked_content, pattern_type = self._mask_string_content(content)
                result = result[:match.start()] + f'"{masked_content}"' + result[match.end():]
                if pattern_type == 'email':
                    stats['emails'] += 1
                elif pattern_type == 'credit_card':
                    stats['credit_cards'] += 1
                elif pattern_type == 'ip_address':
                    stats['ip_addresses'] += 1
                elif pattern_type == 'phone':
                    stats['phones'] += 1
                elif pattern_type == 'ssn':
                    stats['ssns'] += 1
                else:
                    stats['strings'] += 1

        # Mask numeric literals (but not in SQL keywords like LIMIT 10)
        # Only mask numbers in WHERE, SET, VALUES clauses
        number_pattern = re.compile(r'\b(\d+\.?\d*)\b')

        # Find WHERE, SET, VALUES positions
        sensitive_positions = []
        for keyword in ['WHERE', 'SET', 'VALUES', 'HAVING']:
            for match in re.finditer(r'\b' + keyword + r'\b', result, re.IGNORECASE):
                sensitive_positions.append(match.end())

        if sensitive_positions:
            # Only mask numbers after these keywords
            matches = list(number_pattern.finditer(result))
            for match in reversed(matches):
                pos = match.start()
                # Check if this number is after a sensitive keyword
                in_sensitive_area = any(pos > keyword_pos for keyword_pos in sensitive_positions)
                if in_sensitive_area:
                    result = result[:match.start()] + '[NUMBER_REDACTED]' + result[match.end():]
                    stats['numbers'] += 1

        return result, stats

    def _anonymize_moderate(self, sql: str, stats: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
        """
        Moderate anonymization: mask only sensitive data.

        Masks:
        - Email addresses
        - IP addresses
        - Credit card numbers
        - Phone numbers
        - SSNs

        Args:
            sql: SQL query
            stats: Statistics dictionary

        Returns:
            Tuple of (anonymized_sql, updated_stats)
        """
        result = sql
        result, stats = self._mask_sensitive_patterns(result, stats)
        return result, stats

    def _anonymize_minimal(self, sql: str, stats: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
        """
        Minimal anonymization: mask only obvious PII.

        Masks:
        - Email addresses
        - Credit card numbers
        - SSNs

        Args:
            sql: SQL query
            stats: Statistics dictionary

        Returns:
            Tuple of (anonymized_sql, updated_stats)
        """
        result = sql

        # Mask emails
        result, email_count = self._mask_pattern(result, self.patterns['email'], '[EMAIL_REDACTED]')
        stats['emails'] += email_count

        # Mask credit cards
        result, cc_count = self._mask_pattern(result, self.patterns['credit_card'], '[CREDIT_CARD_REDACTED]')
        stats['credit_cards'] += cc_count

        # Mask SSNs
        result, ssn_count = self._mask_pattern(result, self.patterns['ssn'], '[SSN_REDACTED]')
        stats['ssns'] += ssn_count

        return result, stats

    def _mask_sensitive_patterns(self, sql: str, stats: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
        """
        Mask all sensitive patterns.

        Args:
            sql: SQL query
            stats: Statistics dictionary

        Returns:
            Tuple of (anonymized_sql, updated_stats)
        """
        result = sql

        # Order matters: mask most specific patterns first
        # Emails
        result, count = self._mask_pattern(result, self.patterns['email'], '[EMAIL_REDACTED]')
        stats['emails'] += count

        # Credit cards
        result, count = self._mask_pattern(result, self.patterns['credit_card'], '[CREDIT_CARD_REDACTED]')
        stats['credit_cards'] += count

        # SSNs
        result, count = self._mask_pattern(result, self.patterns['ssn'], '[SSN_REDACTED]')
        stats['ssns'] += count

        # Phone numbers
        result, count = self._mask_pattern(result, self.patterns['phone'], '[PHONE_REDACTED]')
        stats['phones'] += count

        # IP addresses (after emails to avoid conflicts)
        result, count = self._mask_pattern(result, self.patterns['ip_address'], '[IP_REDACTED]')
        stats['ip_addresses'] += count

        # Dates and datetimes
        result, count = self._mask_pattern(result, self.patterns['datetime'], '[DATETIME_REDACTED]')
        stats['dates'] += count

        result, count = self._mask_pattern(result, self.patterns['date'], '[DATE_REDACTED]')
        stats['dates'] += count

        return result, stats

    def _mask_pattern(self, text: str, pattern: re.Pattern, replacement: str) -> Tuple[str, int]:
        """
        Mask all occurrences of a pattern.

        Args:
            text: Input text
            pattern: Regex pattern
            replacement: Replacement string

        Returns:
            Tuple of (masked_text, count_of_replacements)
        """
        count = len(pattern.findall(text))
        result = pattern.sub(replacement, text)
        return result, count

    def _mask_string_content(self, content: str) -> Tuple[str, str]:
        """
        Mask string content based on pattern detection.

        Args:
            content: String content (without quotes)

        Returns:
            Tuple of (masked_content, pattern_type)
            pattern_type is one of: email, credit_card, ip_address, phone, ssn, or 'generic'
        """
        # Check for specific patterns in order of priority
        if self.patterns['email'].search(content):
            return '[EMAIL_REDACTED]', 'email'
        elif self.patterns['credit_card'].search(content):
            return '[CREDIT_CARD_REDACTED]', 'credit_card'
        elif self.patterns['ssn'].search(content):
            return '[SSN_REDACTED]', 'ssn'
        elif self.patterns['phone'].search(content):
            return '[PHONE_REDACTED]', 'phone'
        elif self.patterns['ip_address'].search(content):
            return '[IP_REDACTED]', 'ip_address'
        else:
            return '[STRING_REDACTED]', 'generic'

    def _is_sql_keyword(self, text: str) -> bool:
        """
        Check if text is a SQL keyword.

        Args:
            text: Text to check

        Returns:
            True if text is a SQL keyword
        """
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE',
            'DATABASE', 'INDEX', 'VIEW', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
            'OUTER', 'ON', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT',
            'OFFSET', 'UNION', 'ALL', 'DISTINCT', 'COUNT', 'SUM', 'AVG',
            'MIN', 'MAX', 'LIKE', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN',
            'ELSE', 'END', 'ASC', 'DESC', 'VALUES', 'SET', 'DEFAULT', 'PRIMARY',
            'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'CONSTRAINT'
        }
        return text.upper() in sql_keywords


def anonymize_query(sql: str, level: str = "strict") -> Tuple[str, Dict[str, int]]:
    """
    Convenience function to anonymize a SQL query.

    Args:
        sql: Original SQL query
        level: Anonymization level (strict, moderate, minimal)

    Returns:
        Tuple of (anonymized_sql, stats)

    Example:
        >>> anonymize_query("SELECT * FROM users WHERE email = 'john@example.com'")
        ("SELECT * FROM users WHERE email = '[EMAIL_REDACTED]'", {'emails': 1, ...})
    """
    anonymizer = SQLAnonymizer(AnonymizationLevel(level))
    return anonymizer.anonymize(sql)
