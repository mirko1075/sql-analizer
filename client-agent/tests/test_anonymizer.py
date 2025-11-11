"""
Tests for SQL Anonymizer.
"""
import sys
sys.path.insert(0, '..')

from anonymizer import SQLAnonymizer, AnonymizationLevel, anonymize_query


class TestSQLAnonymizerStrict:
    """Tests for strict anonymization level."""

    def test_anonymize_email(self):
        """Test email anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM users WHERE email = 'john@example.com'"
        result, stats = anonymizer.anonymize(sql)

        assert '[EMAIL_REDACTED]' in result
        assert 'john@example.com' not in result
        assert stats['emails'] >= 1

    def test_anonymize_string_values(self):
        """Test string value anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM users WHERE name = 'John Doe'"
        result, stats = anonymizer.anonymize(sql)

        assert '[STRING_REDACTED]' in result or '[EMAIL_REDACTED]' in result
        assert stats['strings'] >= 1 or stats['emails'] >= 1

    def test_anonymize_numeric_values(self):
        """Test numeric value anonymization in WHERE clause."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM users WHERE age = 25 AND salary > 50000"
        result, stats = anonymizer.anonymize(sql)

        # Numbers in WHERE clause should be anonymized
        assert ('25' not in result and '50000' not in result) or '[NUMBER_REDACTED]' in result

    def test_preserve_sql_structure(self):
        """Test that SQL structure is preserved."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM users WHERE email = 'test@test.com'"
        result, stats = anonymizer.anonymize(sql)

        assert 'SELECT' in result
        assert 'FROM' in result
        assert 'WHERE' in result
        assert 'users' in result

    def test_anonymize_credit_card(self):
        """Test credit card anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM payments WHERE card = '4532-1234-5678-9010'"
        result, stats = anonymizer.anonymize(sql)

        assert '[CREDIT_CARD_REDACTED]' in result
        assert '4532-1234-5678-9010' not in result
        assert stats['credit_cards'] >= 1

    def test_anonymize_ip_address(self):
        """Test IP address anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "SELECT * FROM logs WHERE ip = '192.168.1.1'"
        result, stats = anonymizer.anonymize(sql)

        assert '[IP_REDACTED]' in result
        assert '192.168.1.1' not in result
        assert stats['ip_addresses'] >= 1


class TestSQLAnonymizerModerate:
    """Tests for moderate anonymization level."""

    def test_moderate_anonymizes_emails(self):
        """Test that moderate level anonymizes emails."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.MODERATE)
        sql = "SELECT * FROM users WHERE email = 'john@example.com' AND age = 25"
        result, stats = anonymizer.anonymize(sql)

        assert '[EMAIL_REDACTED]' in result
        assert 'john@example.com' not in result
        assert stats['emails'] >= 1


class TestSQLAnonymizerMinimal:
    """Tests for minimal anonymization level."""

    def test_minimal_anonymizes_emails(self):
        """Test that minimal level anonymizes emails."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.MINIMAL)
        sql = "SELECT * FROM users WHERE email = 'john@example.com'"
        result, stats = anonymizer.anonymize(sql)

        assert '[EMAIL_REDACTED]' in result
        assert 'john@example.com' not in result
        assert stats['emails'] >= 1

    def test_minimal_preserves_normal_strings(self):
        """Test that minimal level preserves normal strings."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.MINIMAL)
        sql = "SELECT * FROM users WHERE name = 'John'"
        result, stats = anonymizer.anonymize(sql)

        # Minimal should not anonymize regular strings
        assert 'John' in result or '[STRING_REDACTED]' not in result


class TestConvenienceFunction:
    """Tests for anonymize_query convenience function."""

    def test_anonymize_query_default(self):
        """Test anonymize_query with default settings."""
        sql = "SELECT * FROM users WHERE email = 'test@example.com'"
        result, stats = anonymize_query(sql)

        assert '[EMAIL_REDACTED]' in result
        assert 'test@example.com' not in result

    def test_anonymize_query_strict(self):
        """Test anonymize_query with strict level."""
        sql = "SELECT * FROM users WHERE name = 'Test'"
        result, stats = anonymize_query(sql, level="strict")

        assert '[STRING_REDACTED]' in result or stats['strings'] > 0

    def test_anonymize_query_minimal(self):
        """Test anonymize_query with minimal level."""
        sql = "SELECT * FROM users WHERE email = 'test@test.com'"
        result, stats = anonymize_query(sql, level="minimal")

        assert '[EMAIL_REDACTED]' in result


class TestComplexQueries:
    """Tests for complex SQL queries."""

    def test_join_query(self):
        """Test JOIN query anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = """
            SELECT u.name, o.total
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.email = 'john@example.com' AND o.total > 100
        """
        result, stats = anonymizer.anonymize(sql)

        assert 'SELECT' in result
        assert 'JOIN' in result
        assert '[EMAIL_REDACTED]' in result
        assert 'john@example.com' not in result

    def test_insert_query(self):
        """Test INSERT query anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')"
        result, stats = anonymizer.anonymize(sql)

        assert 'INSERT' in result
        assert '[EMAIL_REDACTED]' in result or '[STRING_REDACTED]' in result
        assert 'john@example.com' not in result

    def test_update_query(self):
        """Test UPDATE query anonymization."""
        anonymizer = SQLAnonymizer(AnonymizationLevel.STRICT)
        sql = "UPDATE users SET email = 'new@example.com' WHERE id = 123"
        result, stats = anonymizer.anonymize(sql)

        assert 'UPDATE' in result
        assert '[EMAIL_REDACTED]' in result
        assert 'new@example.com' not in result


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
