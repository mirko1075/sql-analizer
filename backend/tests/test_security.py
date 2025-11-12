"""
Tests for security utilities: password hashing, JWT, API keys.
"""
import pytest
from datetime import datetime, timedelta
import time

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_token_pair,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    extract_org_id_from_api_key,
    create_request_signature,
    verify_request_signature,
    generate_nonce,
    is_strong_password
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that hashing same password twice produces different hashes (salt)."""
        password = "MySecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPasswordStrength:
    """Tests for password strength validation."""

    def test_strong_password(self):
        """Test that strong passwords are accepted."""
        passwords = [
            "MyPassword123!",
            "Secure@Pass2024",
            "Test!ng123Pass"
        ]

        for password in passwords:
            is_strong, error = is_strong_password(password)
            assert is_strong is True
            assert error is None

    def test_weak_password_too_short(self):
        """Test rejection of short passwords."""
        is_strong, error = is_strong_password("Short1!")
        assert is_strong is False
        assert "8 characters" in error

    def test_weak_password_no_uppercase(self):
        """Test rejection of passwords without uppercase."""
        is_strong, error = is_strong_password("noupppercase123!")
        assert is_strong is False
        assert "uppercase" in error

    def test_weak_password_no_lowercase(self):
        """Test rejection of passwords without lowercase."""
        is_strong, error = is_strong_password("NOLOWERCASE123!")
        assert is_strong is False
        assert "lowercase" in error

    def test_weak_password_no_digit(self):
        """Test rejection of passwords without digits."""
        is_strong, error = is_strong_password("NoDigitsHere!")
        assert is_strong is False
        assert "digit" in error

    def test_weak_password_no_special(self):
        """Test rejection of passwords without special characters."""
        is_strong, error = is_strong_password("NoSpecialChar123")
        assert is_strong is False
        assert "special character" in error


class TestJWT:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {
            "sub": "test@example.com",
            "user_id": 123,
            "org_id": 1
        }

        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test access token decoding."""
        data = {
            "sub": "test@example.com",
            "user_id": 123,
            "org_id": 1
        }

        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == 123
        assert decoded["org_id"] == 1
        assert decoded["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {
            "sub": "test@example.com",
            "user_id": 123
        }

        token = create_refresh_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["type"] == "refresh"

    def test_expired_token(self):
        """Test that expired tokens are rejected."""
        data = {"sub": "test@example.com", "user_id": 123}

        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        # Wait a moment to ensure expiration
        time.sleep(0.1)

        decoded = decode_token(token)
        assert decoded is None  # Expired token returns None

    def test_create_token_pair(self):
        """Test creation of access + refresh token pair."""
        data = {
            "sub": "test@example.com",
            "user_id": 123,
            "org_id": 1,
            "role": "user"
        }

        tokens = create_token_pair(data)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "bearer"

        # Verify both tokens are valid
        access_decoded = decode_token(tokens["access_token"])
        refresh_decoded = decode_token(tokens["refresh_token"])

        assert access_decoded["type"] == "access"
        assert refresh_decoded["type"] == "refresh"


class TestAPIKeys:
    """Tests for API key generation and validation."""

    def test_generate_api_key(self):
        """Test API key generation."""
        org_id = 123
        api_key = generate_api_key(org_id)

        assert api_key is not None
        assert api_key.startswith(f"dbp_{org_id}_")
        assert len(api_key) > 20

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "dbp_123_testkey"
        hashed = hash_api_key(api_key)

        assert hashed is not None
        assert hashed != api_key
        assert len(hashed) == 64  # SHA-256 hex = 64 chars

    def test_verify_api_key_correct(self):
        """Test API key verification with correct key."""
        api_key = generate_api_key(123)
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_incorrect(self):
        """Test API key verification with incorrect key."""
        api_key = generate_api_key(123)
        hashed = hash_api_key(api_key)

        assert verify_api_key("wrong_key", hashed) is False

    def test_extract_org_id_from_api_key(self):
        """Test extracting organization ID from API key."""
        org_id = 456
        api_key = generate_api_key(org_id)

        extracted_id = extract_org_id_from_api_key(api_key)
        assert extracted_id == org_id

    def test_extract_org_id_invalid_format(self):
        """Test extraction with invalid API key format."""
        invalid_keys = [
            "invalid_key",
            "dbp_notanumber_token",
            "wrong_format",
            ""
        ]

        for key in invalid_keys:
            assert extract_org_id_from_api_key(key) is None


class TestRequestSigning:
    """Tests for request signature creation and verification (replay protection)."""

    def test_create_request_signature(self):
        """Test request signature creation."""
        api_key = "test_api_key"
        timestamp = "2024-01-01T12:00:00Z"
        nonce = "random_nonce"
        body = '{"data": "test"}'

        signature = create_request_signature(api_key, timestamp, nonce, body)

        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex

    def test_verify_request_signature_valid(self):
        """Test signature verification with valid signature."""
        api_key = "test_api_key"
        timestamp = datetime.utcnow().isoformat() + "Z"
        nonce = generate_nonce()
        body = '{"data": "test"}'

        signature = create_request_signature(api_key, timestamp, nonce, body)

        is_valid = verify_request_signature(api_key, timestamp, nonce, signature, body)
        assert is_valid is True

    def test_verify_request_signature_invalid(self):
        """Test signature verification with invalid signature."""
        api_key = "test_api_key"
        timestamp = datetime.utcnow().isoformat() + "Z"
        nonce = generate_nonce()
        body = '{"data": "test"}'

        signature = "invalid_signature"

        is_valid = verify_request_signature(api_key, timestamp, nonce, signature, body)
        assert is_valid is False

    def test_verify_request_signature_expired(self):
        """Test that old signatures are rejected."""
        api_key = "test_api_key"
        # Timestamp 10 minutes ago (max_age_seconds default is 300 = 5 min)
        timestamp = (datetime.utcnow() - timedelta(minutes=10)).isoformat() + "Z"
        nonce = generate_nonce()
        body = '{"data": "test"}'

        signature = create_request_signature(api_key, timestamp, nonce, body)

        is_valid = verify_request_signature(api_key, timestamp, nonce, signature, body)
        assert is_valid is False

    def test_verify_request_signature_different_body(self):
        """Test that signature changes if body changes (tampering detection)."""
        api_key = "test_api_key"
        timestamp = datetime.utcnow().isoformat() + "Z"
        nonce = generate_nonce()
        body = '{"data": "original"}'

        signature = create_request_signature(api_key, timestamp, nonce, body)

        # Try to verify with different body
        tampered_body = '{"data": "tampered"}'
        is_valid = verify_request_signature(api_key, timestamp, nonce, signature, tampered_body)
        assert is_valid is False

    def test_generate_nonce(self):
        """Test nonce generation."""
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()

        assert nonce1 != nonce2  # Should be random
        assert len(nonce1) > 0
        assert len(nonce2) > 0


class TestSecurityIntegration:
    """Integration tests for security components."""

    def test_full_authentication_flow(self):
        """Test complete authentication flow: password -> JWT -> verification."""
        # User registration (password hashing)
        password = "MySecurePass123!"
        password_hash = hash_password(password)

        # Login (password verification + token generation)
        assert verify_password(password, password_hash) is True

        token_data = {
            "sub": "user@example.com",
            "user_id": 123,
            "org_id": 1,
            "role": "user"
        }

        tokens = create_token_pair(token_data)

        # Request with access token (token verification)
        decoded = decode_token(tokens["access_token"])
        assert decoded is not None
        assert decoded["user_id"] == 123

        # Token refresh
        refresh_decoded = decode_token(tokens["refresh_token"])
        assert refresh_decoded["type"] == "refresh"

    def test_api_key_full_flow(self):
        """Test complete API key flow: generation -> storage -> verification."""
        org_id = 789

        # Generate API key
        api_key = generate_api_key(org_id)

        # Store hashed version (what would go in database)
        stored_hash = hash_api_key(api_key)

        # Client sends API key, server verifies
        assert verify_api_key(api_key, stored_hash) is True
        assert extract_org_id_from_api_key(api_key) == org_id

        # Wrong key should fail
        wrong_key = generate_api_key(999)
        assert verify_api_key(wrong_key, stored_hash) is False
