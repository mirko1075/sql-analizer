"""
Security utilities for authentication and authorization.
Handles password hashing, JWT tokens, and API key validation.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import secrets
import hashlib
import hmac

# ============================================================================
# PASSWORD HASHING
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production-min-32-chars")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data (should include: sub, org_id, role, etc.)
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token (longer expiration).

    Args:
        data: Payload data (minimal: user_id, org_id)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create both access and refresh tokens.

    Args:
        user_data: User information to encode (user_id, org_id, role, etc.)

    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token({
        "sub": user_data.get("sub"),
        "user_id": user_data.get("user_id"),
        "org_id": user_data.get("org_id")
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

API_KEY_SALT = os.getenv("API_KEY_SALT", "your-api-key-salt-change-this-min-32-chars")


def generate_api_key(org_id: int) -> str:
    """
    Generate a new API key for an organization.

    Format: dbp_{org_id}_{random_token}

    Args:
        org_id: Organization ID

    Returns:
        API key string (plain text, store hash only!)
    """
    random_token = secrets.token_urlsafe(32)
    api_key = f"dbp_{org_id}_{random_token}"
    return api_key


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: Plain text API key

    Returns:
        SHA-256 hash of the API key with salt
    """
    salted = f"{api_key}{API_KEY_SALT}"
    return hashlib.sha256(salted.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.

    Args:
        api_key: Plain text API key to verify
        stored_hash: Stored hash from database

    Returns:
        True if valid, False otherwise
    """
    key_hash = hash_api_key(api_key)
    return key_hash == stored_hash


def extract_org_id_from_api_key(api_key: str) -> Optional[int]:
    """
    Extract organization ID from API key format.

    Args:
        api_key: API key string (dbp_{org_id}_{token})

    Returns:
        Organization ID or None if invalid format
    """
    try:
        parts = api_key.split("_")
        if len(parts) >= 3 and parts[0] == "dbp":
            return int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


# ============================================================================
# REQUEST SIGNING (for client agent authentication)
# ============================================================================

def create_request_signature(api_key: str, timestamp: str, nonce: str, body: str = "") -> str:
    """
    Create a request signature for replay protection.

    Signature = HMAC-SHA256(api_key, timestamp + nonce + body)

    Args:
        api_key: Organization API key
        timestamp: ISO timestamp of request
        nonce: Random nonce (prevents replay attacks)
        body: Request body (if any)

    Returns:
        Hex-encoded signature
    """
    message = f"{timestamp}{nonce}{body}"
    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_request_signature(
    api_key: str,
    timestamp: str,
    nonce: str,
    signature: str,
    body: str = "",
    max_age_seconds: int = 300
) -> bool:
    """
    Verify a request signature and check timestamp freshness.

    Args:
        api_key: Organization API key
        timestamp: ISO timestamp from request
        nonce: Nonce from request
        signature: Signature to verify
        body: Request body
        max_age_seconds: Maximum age of request (default 5 minutes)

    Returns:
        True if signature valid and timestamp fresh, False otherwise
    """
    # Check timestamp freshness
    try:
        request_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        age = (datetime.utcnow() - request_time.replace(tzinfo=None)).total_seconds()

        if age > max_age_seconds or age < -60:  # Allow 1 minute clock skew
            return False
    except (ValueError, AttributeError):
        return False

    # Verify signature
    expected_signature = create_request_signature(api_key, timestamp, nonce, body)
    return hmac.compare_digest(signature, expected_signature)


# ============================================================================
# SECURITY HELPERS
# ============================================================================

def generate_nonce() -> str:
    """Generate a random nonce for request signing."""
    return secrets.token_urlsafe(16)


def is_strong_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Check if password meets strength requirements.

    Requirements:
    - At least 8 characters
    - Contains uppercase and lowercase
    - Contains digit
    - Contains special character

    Args:
        password: Password to check

    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"

    return True, None
