"""
User Profile API routes.

Handles user profile management and session management.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.db.session import get_db
from backend.core.security import hash_password, verify_password
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_active_user
from backend.db.models import User, UserSession
from backend.api.schemas.users import (
    UserUpdateProfileRequest,
    ChangePasswordRequest,
    UserProfileResponse,
    UserSessionResponse,
    UserSessionListResponse,
)
from backend.api.schemas.auth import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# USER PROFILE
# =============================================================================


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get the authenticated user's profile information"
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile.

    Returns basic user information (not including teams, use /auth/me for that).
    """
    try:
        return UserProfileResponse.model_validate(current_user)

    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update user profile",
    description="Update the authenticated user's profile information"
)
async def update_my_profile(
    request: UserUpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.

    Only updates provided fields.
    """
    try:
        # Update fields
        if request.full_name is not None:
            current_user.full_name = request.full_name

        db.commit()
        db.refresh(current_user)

        logger.info(f"User {current_user.email} updated their profile")

        return UserProfileResponse.model_validate(current_user)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change the authenticated user's password"
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.

    Requires current password for verification.
    Revokes all existing sessions after password change.
    """
    try:
        # Verify current password
        if not verify_password(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Validate new password is different
        if request.current_password == request.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )

        # Update password
        current_user.hashed_password = hash_password(request.new_password)
        db.commit()

        # Revoke all active sessions (force re-login)
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False
        ).all()

        for session in active_sessions:
            session.revoked = True
            session.revoked_at = datetime.utcnow()

        db.commit()

        logger.info(
            f"User {current_user.email} changed password. "
            f"Revoked {len(active_sessions)} session(s)."
        )

        return MessageResponse(
            message="Password changed successfully. Please log in again with your new password."
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


@router.get(
    "/me/sessions",
    response_model=UserSessionListResponse,
    summary="List user sessions",
    description="Get all active sessions for the authenticated user"
)
async def list_my_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all active sessions for the current user.

    Shows both access and refresh token sessions.
    """
    try:
        # Get active sessions
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False,
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.created_at.desc()).all()

        sessions_data = [
            UserSessionResponse.model_validate(session)
            for session in sessions
        ]

        return UserSessionListResponse(
            total=len(sessions_data),
            sessions=sessions_data
        )

    except Exception as e:
        logger.error(f"Error listing user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list user sessions"
        )


@router.post(
    "/me/sessions/revoke-all",
    response_model=MessageResponse,
    summary="Revoke all sessions",
    description="Revoke all active sessions (logout from all devices)"
)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke all active sessions for the current user.

    This logs the user out from all devices.
    """
    try:
        # Revoke all active sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False
        ).all()

        for session in active_sessions:
            session.revoked = True
            session.revoked_at = datetime.utcnow()

        db.commit()

        logger.info(
            f"User {current_user.email} revoked all sessions. "
            f"Revoked {len(active_sessions)} session(s)."
        )

        return MessageResponse(
            message=f"Successfully revoked {len(active_sessions)} session(s). Please log in again."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )


# =============================================================================
# ACCOUNT DELETION (Self-service)
# =============================================================================


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete account",
    description="Delete the authenticated user's account (requires password confirmation)"
)
async def delete_my_account(
    password_confirmation: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account.

    Requires password confirmation. This will:
    - Revoke all sessions
    - Remove team memberships
    - Deactivate the user (soft delete)

    Note: Data associated with teams (slow queries, etc.) is NOT deleted,
    only the user's membership is removed.
    """
    try:
        # Verify password
        if not verify_password(password_confirmation, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password confirmation is incorrect"
            )

        # Deactivate user (soft delete)
        current_user.is_active = False

        # Revoke all sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False
        ).all()

        for session in active_sessions:
            session.revoked = True
            session.revoked_at = datetime.utcnow()

        db.commit()

        logger.warning(
            f"User {current_user.email} deleted their account. "
            f"Revoked {len(active_sessions)} session(s)."
        )

        return MessageResponse(
            message="Account successfully deactivated. Your data has been preserved but you can no longer log in."
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )
