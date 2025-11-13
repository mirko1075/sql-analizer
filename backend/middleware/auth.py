"""
Authentication middleware for JWT and API Key validation.
Handles user authentication and organization API key authentication.
"""
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Annotated
from datetime import datetime

from db.models_multitenant import User, Organization, Collector, get_db, UserRole
from core.security import decode_token, verify_api_key, extract_org_id_from_api_key
import re

# Security scheme for JWT tokens
security = HTTPBearer()


# ============================================================================
# EXCEPTIONS
# ============================================================================

class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Raised when user lacks required permissions."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# ============================================================================
# JWT AUTHENTICATION (for User Login)
# ============================================================================

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.

    Usage in route:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")

    # Verify token type
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    # Extract user ID
    user_id = payload.get("user_id")
    if not user_id:
        raise AuthenticationError("Token missing user_id claim")

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError("User not found")

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and ensure they're active.
    (Redundant check, but useful for explicit dependencies)
    """
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


# ============================================================================
# OPTIONAL JWT AUTHENTICATION
# ============================================================================

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token, but don't fail if not present.
    Returns None if no valid token.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user


# ============================================================================
# API KEY AUTHENTICATION (for Client Agents)
# ============================================================================

async def get_organization_from_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
    db: Session = Depends(get_db)
) -> Organization:
    """
    Validate API key and return organization.

    Client agents must send API key in X-API-Key header.

    Usage in route:
        @app.post("/api/v1/client/queries")
        async def receive_queries(
            org: Organization = Depends(get_organization_from_api_key)
        ):
            # org.id is the organization ID
            ...
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )

    # Extract organization ID from key format
    org_id = extract_org_id_from_api_key(x_api_key)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )

    # Fetch organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Verify API key
    if not org.api_key_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization has no API key configured"
        )

    if not verify_api_key(x_api_key, org.api_key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check expiration
    if org.api_key_expires_at and org.api_key_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    return org


# ============================================================================
# COLLECTOR API KEY AUTHENTICATION
# ============================================================================

def extract_collector_id_from_api_key(api_key: str) -> Optional[int]:
    """
    Extract collector ID from API key.

    Format: collector_{id}_{token}
    Example: collector_5_abc123...
    """
    match = re.match(r'^collector_(\d+)_', api_key)
    if match:
        return int(match.group(1))
    return None


async def get_collector_from_api_key(
    x_collector_api_key: Annotated[Optional[str], Header()] = None,
    db: Session = Depends(get_db)
) -> Collector:
    """
    Validate collector API key and return collector.

    Collector agents must send API key in X-Collector-API-Key header.

    Usage in route:
        @app.post("/api/v1/collectors/heartbeat")
        async def heartbeat(
            collector: Collector = Depends(get_collector_from_api_key)
        ):
            # collector.id, collector.organization_id, etc.
            ...
    """
    if not x_collector_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Collector-API-Key header"
        )

    # Extract collector ID from key format
    collector_id = extract_collector_id_from_api_key(x_collector_api_key)
    if not collector_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collector API key format"
        )

    # Fetch collector
    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collector API key"
        )

    # Verify API key
    if not collector.api_key_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collector has no API key configured"
        )

    if not collector.verify_api_key(x_collector_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collector API key"
        )

    return collector


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

class RoleChecker:
    """
    Dependency for checking user roles.

    Usage:
        @app.get("/admin/users")
        async def list_users(
            user: User = Depends(get_current_user),
            _: None = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]))
        ):
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}"
            )
        return None


# Convenience role checkers
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_org_admin = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN])
require_team_lead = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.TEAM_LEAD])


# ============================================================================
# ORGANIZATION ACCESS CONTROL
# ============================================================================

def check_organization_access(user: User, org_id: int):
    """
    Check if user has access to an organization.

    Super admins: access to all organizations
    Other users: only their own organization

    Raises:
        AuthorizationError: If user doesn't have access
    """
    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin has access to everything

    if user.organization_id != org_id:
        raise AuthorizationError("Access denied to this organization")


def check_team_access(user: User, team_id: int, db: Session):
    """
    Check if user has access to a team.

    Super admins: access to all teams
    Org admins: access to teams in their organization
    Team leads/users: only their own team

    Raises:
        AuthorizationError: If user doesn't have access
    """
    from db.models_multitenant import Team

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin has access to everything

    if user.role == UserRole.ORG_ADMIN:
        if team.organization_id != user.organization_id:
            raise AuthorizationError("Access denied to this team")
        return

    # Team lead or regular user: must be in the same team
    if not user.identity_id:
        raise AuthorizationError("User not assigned to any team")

    from db.models_multitenant import Identity
    identity = db.query(Identity).filter(Identity.id == user.identity_id).first()
    if not identity or identity.team_id != team_id:
        raise AuthorizationError("Access denied to this team")


def check_identity_access(user: User, identity_id: int, db: Session):
    """
    Check if user has access to an identity.

    Super admins: access to all identities
    Org admins: access to identities in their organization
    Team leads: access to identities in their team
    Users: only their own identity

    Raises:
        AuthorizationError: If user doesn't have access
    """
    from db.models_multitenant import Identity

    identity = db.query(Identity).filter(Identity.id == identity_id).first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin has access to everything

    if user.role == UserRole.ORG_ADMIN:
        # Check if identity belongs to user's organization
        from db.models_multitenant import Team
        team = db.query(Team).filter(Team.id == identity.team_id).first()
        if team and team.organization_id == user.organization_id:
            return
        raise AuthorizationError("Access denied to this identity")

    if user.role == UserRole.TEAM_LEAD:
        # Check if identity belongs to user's team
        if user.identity_id:
            user_identity = db.query(Identity).filter(Identity.id == user.identity_id).first()
            if user_identity and user_identity.team_id == identity.team_id:
                return
        raise AuthorizationError("Access denied to this identity")

    # Regular user: only their own identity
    if user.identity_id != identity_id:
        raise AuthorizationError("Access denied to this identity")


def check_collector_access(user: User, collector_id: int, db: Session):
    """
    Check if user has access to a collector.

    Super admins: access to all collectors
    Org admins: access to collectors in their organization
    Team leads: access to collectors in their team
    Users: no direct access to collectors

    Raises:
        AuthorizationError: If user doesn't have access
    """
    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    if user.role == UserRole.SUPER_ADMIN:
        return  # Super admin has access to everything

    if user.role == UserRole.ORG_ADMIN:
        if collector.organization_id != user.organization_id:
            raise AuthorizationError("Access denied to this collector")
        return

    if user.role == UserRole.TEAM_LEAD:
        # Check if collector belongs to user's team
        if not user.identity_id:
            raise AuthorizationError("User not assigned to any team")

        from db.models_multitenant import Identity
        identity = db.query(Identity).filter(Identity.id == user.identity_id).first()
        if identity and identity.team_id == collector.team_id:
            return
        raise AuthorizationError("Access denied to this collector")

    # Regular users cannot manage collectors
    raise AuthorizationError("Insufficient permissions to access collectors")


# ============================================================================
# HYBRID AUTHENTICATION (JWT or API Key)
# ============================================================================

async def get_current_principal(
    request: Request,
    db: Session = Depends(get_db)
) -> tuple[Optional[User], Optional[Organization]]:
    """
    Get authentication principal - either User (JWT) or Organization (API Key).

    Returns:
        (user, organization) tuple. One will be set, the other None.

    Usage:
        @app.post("/api/v1/queries")
        async def submit_query(
            principal: tuple = Depends(get_current_principal)
        ):
            user, org = principal
            if user:
                # Authenticated as user
                org_id = user.organization_id
            elif org:
                # Authenticated as organization (client agent)
                org_id = org.id
    """
    # Try JWT first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
                if user:
                    return (user, None)

    # Try API Key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        org_id = extract_org_id_from_api_key(api_key)
        if org_id:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org and org.api_key_hash and verify_api_key(api_key, org.api_key_hash):
                if not org.api_key_expires_at or org.api_key_expires_at >= datetime.utcnow():
                    return (None, org)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials"
    )
