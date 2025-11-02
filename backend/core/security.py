"""
Security utilities for authentication, password hashing, and encryption.

Provides functions for:
- Password hashing and verification (bcrypt)
- JWT token creation and validation
- Database password encryption/decryption (Fernet)
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from passlib.context import CryptContext
from jose import JWTError, jwt
from cryptography.fernet import Fernet

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# PASSWORD HASHING (Bcrypt)
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# =============================================================================
# JWT TOKEN MANAGEMENT
# =============================================================================


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (usually user_id)
        expires_delta: Token expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES from config)
        additional_claims: Additional data to include in token payload

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta

    # Standard JWT claims
    to_encode = {
        "sub": str(subject),  # Subject (user ID)
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
        "jti": secrets.token_urlsafe(32),  # JWT ID (unique identifier)
        "type": "access"  # Token type
    }

    # Add any additional claims
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens have a longer expiration time and are used to obtain new access tokens.

    Args:
        subject: Token subject (usually user_id)
        expires_delta: Token expiration time (defaults to REFRESH_TOKEN_EXPIRE_DAYS from config)
        additional_claims: Additional data to include in token payload

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(32),
        "type": "refresh"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: Encoded JWT token

    Returns:
        Token payload as dictionary

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise


def extract_token_jti(token: str) -> Optional[str]:
    """
    Extract the JTI (JWT ID) claim from a token without full validation.

    This is useful for logout/revocation where you need the JTI
    even if the token is expired.

    Args:
        token: Encoded JWT token

    Returns:
        JTI string or None if extraction fails
    """
    try:
        # Decode without verification to get JTI
        unverified_payload = jwt.get_unverified_claims(token)
        return unverified_payload.get("jti")
    except Exception as e:
        logger.error(f"Failed to extract JTI from token: {e}")
        return None


# =============================================================================
# DATABASE PASSWORD ENCRYPTION (Fernet)
# =============================================================================

# Initialize Fernet cipher with the encryption key from config
_fernet_cipher = None


def _get_fernet_cipher() -> Fernet:
    """
    Get or create the Fernet cipher instance.

    Lazy initialization to ensure settings are loaded.
    """
    global _fernet_cipher
    if _fernet_cipher is None:
        _fernet_cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet_cipher


def encrypt_db_password(plain_password: str) -> str:
    """
    Encrypt a database password using Fernet symmetric encryption.

    This is used to securely store database connection passwords.

    Args:
        plain_password: Plain text database password

    Returns:
        Encrypted password (base64 encoded string)
    """
    try:
        cipher = _get_fernet_cipher()
        encrypted = cipher.encrypt(plain_password.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Password encryption error: {e}")
        raise ValueError("Failed to encrypt password")


def decrypt_db_password(encrypted_password: str) -> str:
    """
    Decrypt a database password.

    Args:
        encrypted_password: Encrypted password string (base64 encoded)

    Returns:
        Decrypted plain text password

    Raises:
        ValueError: If decryption fails
    """
    try:
        cipher = _get_fernet_cipher()
        decrypted = cipher.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise ValueError("Failed to decrypt password")


def generate_fernet_key() -> str:
    """
    Generate a new Fernet encryption key.

    This should be run once during initial setup and stored in the .env file.

    Returns:
        Base64 encoded Fernet key
    """
    key = Fernet.generate_key()
    return key.decode()


# =============================================================================
# TOKEN VALIDATION HELPERS
# =============================================================================


def validate_token_type(token_payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Validate that a token has the expected type (access or refresh).

    Args:
        token_payload: Decoded JWT payload
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise
    """
    token_type = token_payload.get("type")
    if token_type != expected_type:
        logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
        return False
    return True


def is_token_expired(token_payload: Dict[str, Any]) -> bool:
    """
    Check if a token is expired based on its payload.

    Args:
        token_payload: Decoded JWT payload

    Returns:
        True if token is expired, False otherwise
    """
    exp_timestamp = token_payload.get("exp")
    if not exp_timestamp:
        return True

    exp_datetime = datetime.fromtimestamp(exp_timestamp)
    return datetime.utcnow() > exp_datetime


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def generate_random_password(length: int = 16) -> str:
    """
    Generate a secure random password.

    Useful for creating temporary passwords for new users.

    Args:
        length: Password length (default 16 characters)

    Returns:
        Random password string
    """
    return secrets.token_urlsafe(length)


def create_tokens_pair(user_id: str) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.

    Convenience function for login flow.

    Args:
        user_id: User ID (UUID as string)

    Returns:
        Dictionary with "access_token" and "refresh_token" keys
    """
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
