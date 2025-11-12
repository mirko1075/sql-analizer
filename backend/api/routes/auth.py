"""
Authentication routes: login, logout, token refresh, password management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from db.models_multitenant import User, get_db, UserRole
from core.security import (
    verify_password,
    hash_password,
    create_token_pair,
    decode_token,
    is_strong_password
)
from middleware.auth import get_current_user, get_current_active_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    old_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    """Password reset request model (for admins)."""
    user_id: int
    new_password: str


class UserProfileResponse(BaseModel):
    """User profile response model."""
    id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_id: int
    organization_name: str
    identity_id: Optional[int]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.

    Returns JWT access token and refresh token.

    **Example:**
    ```json
    {
        "email": "admin@dbpower.local",
        "password": "admin123"
    }
    ```
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create token payload
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "identity_id": user.identity_id
    }

    # Generate tokens
    tokens = create_token_pair(token_data)

    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "organization_id": user.organization_id,
            "identity_id": user.identity_id
        }
    )


@router.post("/token", response_model=LoginResponse)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2-compatible login endpoint.

    Uses username/password form data (for compatibility with OAuth2 clients).
    Username is treated as email.
    """
    login_request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login(login_request, db)


@router.post("/refresh")
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    **Example:**
    ```json
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    """
    # Decode refresh token
    payload = decode_token(refresh_data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    # Get user
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new token payload
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "identity_id": user.identity_id
    }

    # Generate new tokens
    tokens = create_token_pair(token_data)

    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "organization_id": user.organization_id,
            "identity_id": user.identity_id
        }
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    User logout endpoint.

    Note: JWT tokens are stateless, so logout is handled client-side
    by deleting the token. This endpoint is mainly for audit logging.
    """
    return {
        "message": "Logout successful",
        "user_id": current_user.id
    }


# ============================================================================
# USER PROFILE
# ============================================================================

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information.
    """
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization.name,
        identity_id=current_user.identity_id,
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.

    **Example:**
    ```json
    {
        "old_password": "current_password",
        "new_password": "NewSecurePass123!"
    }
    ```
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Check new password strength
    is_strong, error_msg = is_strong_password(password_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset another user's password (admin only).

    Requires ORG_ADMIN or SUPER_ADMIN role.

    **Example:**
    ```json
    {
        "user_id": 123,
        "new_password": "TempPassword123!"
    }
    ```
    """
    # Check if current user is admin
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reset passwords"
        )

    # Get target user
    target_user = db.query(User).filter(User.id == reset_data.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Org admins can only reset passwords within their organization
    if current_user.role == UserRole.ORG_ADMIN:
        if target_user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot reset password for users in other organizations"
            )

    # Check new password strength
    is_strong, error_msg = is_strong_password(reset_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Update password
    target_user.password_hash = hash_password(reset_data.new_password)
    db.commit()

    return {
        "message": "Password reset successfully",
        "user_id": target_user.id,
        "email": target_user.email
    }


# ============================================================================
# TOKEN VALIDATION
# ============================================================================

@router.get("/validate")
async def validate_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate current JWT token.

    Returns 200 if token is valid, 401 otherwise.
    Useful for client-side token validation.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value
    }
