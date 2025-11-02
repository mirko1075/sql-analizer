"""
Authentication API routes.

Handles user registration, login, token refresh, logout, and user profile.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from backend.db.session import get_db
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_token_type,
    extract_token_jti,
    create_tokens_pair
)
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_user, get_current_active_user
from backend.db.models import User, Organization, Team, TeamMember, UserSession
from backend.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
    UserDetailResponse,
    MessageResponse,
    ErrorResponse
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# =============================================================================
# REGISTRATION
# =============================================================================


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password. Automatically creates a default organization and team.",
    responses={
        201: {"description": "User successfully registered"},
        400: {"description": "Email already registered or validation error", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    - Creates user account with hashed password
    - Automatically creates a default organization for the user
    - Creates a "Main Team" within that organization
    - Adds user as OWNER of the team
    - Returns JWT access and refresh tokens
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user with hashed password
        hashed_pw = hash_password(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            is_active=True,
            is_superuser=False
        )
        db.add(new_user)
        db.flush()  # Get user ID without committing

        logger.info(f"Created new user: {new_user.email} (ID: {new_user.id})")

        # Create default organization for the user
        # Generate slug from email (e.g., "john.doe@example.com" -> "john-doe")
        username_part = request.email.split('@')[0]
        org_slug = username_part.replace('.', '-').replace('_', '-').lower()

        # Ensure unique slug
        base_slug = org_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        new_org = Organization(
            name=f"{request.full_name}'s Organization",
            slug=org_slug,
            description=f"Default organization for {request.full_name}",
            plan_type='FREE',
            is_active=True
        )
        db.add(new_org)
        db.flush()

        logger.info(f"Created default organization: {new_org.name} (slug: {new_org.slug})")

        # Create default team
        new_team = Team(
            organization_id=new_org.id,
            name="Main Team",
            description="Default team for query analysis",
            is_active=True
        )
        db.add(new_team)
        db.flush()

        logger.info(f"Created default team: {new_team.name} (ID: {new_team.id})")

        # Add user as OWNER of the team
        team_member = TeamMember(
            team_id=new_team.id,
            user_id=new_user.id,
            role='OWNER'
        )
        db.add(team_member)

        # Create JWT tokens
        access_token = create_access_token(subject=str(new_user.id))
        refresh_token = create_refresh_token(subject=str(new_user.id))

        # Decode tokens to get JTIs and expiration times
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        # Store sessions for token tracking
        access_session = UserSession(
            user_id=new_user.id,
            token_jti=access_payload['jti'],
            token_type='access',
            expires_at=datetime.fromtimestamp(access_payload['exp']),
            revoked=False
        )
        refresh_session = UserSession(
            user_id=new_user.id,
            token_jti=refresh_payload['jti'],
            token_type='refresh',
            expires_at=datetime.fromtimestamp(refresh_payload['exp']),
            revoked=False
        )
        db.add(access_session)
        db.add(refresh_session)

        # Commit all changes
        db.commit()

        logger.info(f"User {new_user.email} registered successfully")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


# =============================================================================
# LOGIN
# =============================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email and password, receive JWT tokens",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
        403: {"description": "Account disabled", "model": ErrorResponse}
    }
)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    - Verifies email and password
    - Creates new access and refresh tokens
    - Tracks session for audit and revocation
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            logger.warning(f"Failed login attempt for user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact administrator."
            )

        # Create JWT tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        # Decode tokens to get JTIs and expiration times
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        # Extract client info for audit
        user_agent = http_request.headers.get("user-agent")
        ip_address = http_request.client.host if http_request.client else None

        # Store sessions for token tracking
        access_session = UserSession(
            user_id=user.id,
            token_jti=access_payload['jti'],
            token_type='access',
            expires_at=datetime.fromtimestamp(access_payload['exp']),
            revoked=False,
            user_agent=user_agent,
            ip_address=ip_address
        )
        refresh_session = UserSession(
            user_id=user.id,
            token_jti=refresh_payload['jti'],
            token_type='refresh',
            expires_at=datetime.fromtimestamp(refresh_payload['exp']),
            revoked=False,
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.add(access_session)
        db.add(refresh_session)
        db.commit()

        logger.info(f"User {user.email} logged in successfully from {ip_address}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# =============================================================================
# TOKEN REFRESH
# =============================================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token",
    responses={
        200: {"description": "New access token created"},
        401: {"description": "Invalid or expired refresh token", "model": ErrorResponse}
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.

    - Validates refresh token
    - Creates new access token
    - Does not create new refresh token (use existing one)
    """
    try:
        # Decode and validate refresh token
        try:
            payload = decode_token(request.refresh_token)
        except JWTError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Validate token type
        if not validate_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected refresh token."
            )

        user_id = payload.get("sub")
        token_jti = payload.get("jti")

        # Check if refresh token is revoked
        session = db.query(UserSession).filter(
            UserSession.token_jti == token_jti,
            UserSession.token_type == 'refresh',
            UserSession.revoked == False
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        # Verify user exists and is active
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        # Create new access token
        access_token = create_access_token(subject=str(user.id))
        access_payload = decode_token(access_token)

        # Store new access token session
        access_session = UserSession(
            user_id=user.id,
            token_jti=access_payload['jti'],
            token_type='access',
            expires_at=datetime.fromtimestamp(access_payload['exp']),
            revoked=False
        )
        db.add(access_session)
        db.commit()

        logger.info(f"Access token refreshed for user: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


# =============================================================================
# LOGOUT
# =============================================================================


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Revoke current access and refresh tokens",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Invalid token", "model": ErrorResponse}
    }
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking their tokens.

    - Extracts JTI from access token
    - Marks all user sessions (access + refresh) as revoked
    """
    try:
        token = credentials.credentials

        # Extract JTI from token (even if expired)
        token_jti = extract_token_jti(token)
        if not token_jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Find the session
        session = db.query(UserSession).filter(
            UserSession.token_jti == token_jti
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found"
            )

        user_id = session.user_id

        # Revoke ALL active sessions for this user (access + refresh)
        # This logs the user out from all devices
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.revoked == False
        ).all()

        for sess in active_sessions:
            sess.revoked = True
            sess.revoked_at = datetime.utcnow()

        db.commit()

        logger.info(f"User {user_id} logged out. Revoked {len(active_sessions)} session(s).")

        return MessageResponse(message="Successfully logged out")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# =============================================================================
# USER PROFILE
# =============================================================================


@router.get(
    "/me",
    response_model=UserDetailResponse,
    summary="Get current user profile",
    description="Get authenticated user's profile with teams",
    responses={
        200: {"description": "User profile retrieved"},
        401: {"description": "Not authenticated", "model": ErrorResponse}
    }
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.

    Returns user information along with their teams and roles.
    """
    try:
        # Fetch user with teams
        user = db.query(User).filter(User.id == current_user.id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Build teams list with roles
        teams_data = []
        for membership in user.team_memberships:
            team = membership.team
            teams_data.append({
                "id": team.id,
                "name": team.name,
                "role": membership.role,
                "organization_id": team.organization_id
            })

        # Build response
        response_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "teams": teams_data
        }

        return UserDetailResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )
