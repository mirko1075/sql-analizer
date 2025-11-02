"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection functions for:
- User authentication (JWT token validation)
- User authorization (role checking)
- Team context management
"""
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import User, UserSession, Team, TeamMember
from backend.core.security import decode_token, validate_token_type
from backend.core.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

# =============================================================================
# USER AUTHENTICATION DEPENDENCIES
# =============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Validates the JWT token, checks if it's not revoked, and returns the user.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException 401: If token is invalid, expired, or revoked
        HTTPException 404: If user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        token = credentials.credentials
        payload = decode_token(token)

        # Validate token type
        if not validate_token_type(payload, "access"):
            raise credentials_exception

        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Extract JTI for session validation
        token_jti: str = payload.get("jti")

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception

    # Check if token is revoked (logout)
    if token_jti:
        session = db.query(UserSession).filter(
            UserSession.token_jti == token_jti,
            UserSession.revoked == False
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.

    Ensures the user account is active (not disabled).

    Args:
        current_user: Current authenticated user

    Returns:
        User object if active

    Raises:
        HTTPException 403: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user and verify they are a superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if superuser

    Raises:
        HTTPException 403: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires superuser privileges"
        )
    return current_user


# =============================================================================
# TEAM CONTEXT DEPENDENCIES
# =============================================================================


async def get_current_team(
    x_team_id: Optional[str] = Header(None, alias="X-Team-ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Team:
    """
    Get the current team context.

    If X-Team-ID header is provided, use that team.
    Otherwise, use the user's first team (default team).

    Args:
        x_team_id: Optional team ID from HTTP header
        current_user: Current authenticated user
        db: Database session

    Returns:
        Team object

    Raises:
        HTTPException 404: If team not found or user not a member
        HTTPException 403: If user not authorized for this team
    """
    # If team ID provided in header, use it
    if x_team_id:
        try:
            team_id = UUID(x_team_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid team ID format"
            )

        # Check if user is member of this team
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )

        # Get team
        team = db.query(Team).filter(
            Team.id == team_id,
            Team.is_active == True
        ).first()

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found or inactive"
            )

        return team

    # No team ID provided, use user's default team (first team)
    membership = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of any team. Please create or join a team."
        )

    team = db.query(Team).filter(
        Team.id == membership.team_id,
        Team.is_active == True
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Default team not found or inactive"
        )

    return team


async def get_user_team_role(
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
) -> str:
    """
    Get the user's role in the current team.

    Args:
        current_user: Current authenticated user
        current_team: Current team context
        db: Database session

    Returns:
        Role string (OWNER, ADMIN, MEMBER, VIEWER)

    Raises:
        HTTPException 404: If membership not found
    """
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == current_team.id,
        TeamMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team membership not found"
        )

    return membership.role


# =============================================================================
# ROLE-BASED AUTHORIZATION DEPENDENCIES
# =============================================================================


def require_role(allowed_roles: List[str]):
    """
    Create a dependency that requires specific role(s).

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(["OWNER", "ADMIN"]))])

    Args:
        allowed_roles: List of allowed roles (OWNER, ADMIN, MEMBER, VIEWER)

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        current_team: Team = Depends(get_current_team),
        db: Session = Depends(get_db)
    ):
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == current_team.id,
            TeamMember.user_id == current_user.id
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )

        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation requires one of these roles: {', '.join(allowed_roles)}"
            )

        return membership

    return role_checker


# Convenience dependencies for common role checks
owner_required = Depends(require_role(["OWNER"]))
admin_required = Depends(require_role(["OWNER", "ADMIN"]))
member_required = Depends(require_role(["OWNER", "ADMIN", "MEMBER"]))
viewer_or_above = Depends(require_role(["OWNER", "ADMIN", "MEMBER", "VIEWER"]))


# =============================================================================
# OPTIONAL AUTH (for public + private endpoints)
# =============================================================================


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.

    Useful for endpoints that work both with and without authentication.

    Args:
        credentials: Optional HTTP Bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        # Reuse get_current_user logic
        token = credentials.credentials
        payload = decode_token(token)

        if not validate_token_type(payload, "access"):
            return None

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user

    except JWTError:
        return None

    return None


# =============================================================================
# HELPER FUNCTIONS (not FastAPI dependencies)
# =============================================================================


def check_user_permission(
    user: User,
    team: Team,
    required_role: str,
    db: Session
) -> bool:
    """
    Check if a user has a specific role or higher in a team.

    Role hierarchy: OWNER > ADMIN > MEMBER > VIEWER

    Args:
        user: User to check
        team: Team to check membership in
        required_role: Minimum required role
        db: Database session

    Returns:
        True if user has required role or higher, False otherwise
    """
    role_hierarchy = {
        "VIEWER": 1,
        "MEMBER": 2,
        "ADMIN": 3,
        "OWNER": 4
    }

    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id
    ).first()

    if not membership:
        return False

    user_role_level = role_hierarchy.get(membership.role, 0)
    required_role_level = role_hierarchy.get(required_role, 0)

    return user_role_level >= required_role_level


def get_user_teams(user: User, db: Session) -> List[Team]:
    """
    Get all teams a user is a member of.

    Args:
        user: User object
        db: Database session

    Returns:
        List of Team objects
    """
    memberships = db.query(TeamMember).filter(
        TeamMember.user_id == user.id
    ).all()

    team_ids = [m.team_id for m in memberships]

    teams = db.query(Team).filter(
        Team.id.in_(team_ids),
        Team.is_active == True
    ).all()

    return teams
