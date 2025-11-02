"""
Pydantic schemas for authentication API.

Defines request and response models for:
- User registration
- Login
- Token refresh
- Logout
- User profile
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# =============================================================================
# AUTHENTICATION REQUEST SCHEMAS
# =============================================================================


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "mirko.siddi@gmail.com",
                "password": "SecurePass123!",
                "full_name": "Mirko Siddi"
            }
        }
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "mirko.siddi@gmail.com",
                "password": "SecurePass123!"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""
    refresh_token: str = Field(..., description="Valid refresh token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass456!"
            }
        }
    )


# =============================================================================
# AUTHENTICATION RESPONSE SCHEMAS
# =============================================================================


class TokenResponse(BaseModel):
    """Response schema for successful authentication."""
    access_token: str = Field(..., description="JWT access token (short-lived)")
    refresh_token: str = Field(..., description="JWT refresh token (long-lived)")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiry time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE1MTYyMzkwMjJ9.abc123xyz",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class UserProfileResponse(BaseModel):
    """Response schema for user profile information."""
    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    is_active: bool = Field(..., description="Whether the user account is active")
    is_superuser: bool = Field(..., description="Whether the user has superuser privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "mirko.siddi@gmail.com",
                "full_name": "Mirko Siddi",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-11-01T10:30:00Z"
            }
        }
    )


# =============================================================================
# NESTED SCHEMAS FOR COMPLEX RESPONSES
# =============================================================================


class TeamBriefSchema(BaseModel):
    """Brief team information for user profile."""
    id: UUID = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    role: str = Field(..., description="User's role in this team (OWNER, ADMIN, MEMBER, VIEWER)")
    organization_id: UUID = Field(..., description="Parent organization ID")

    model_config = ConfigDict(from_attributes=True)


class OrganizationBriefSchema(BaseModel):
    """Brief organization information."""
    id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="URL-friendly organization identifier")
    plan_type: str = Field(..., description="Subscription plan (FREE, PRO, ENTERPRISE)")

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Detailed user profile with organizations and teams."""
    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    teams: List[TeamBriefSchema] = Field(default_factory=list, description="Teams the user belongs to")
    # organizations: List[OrganizationBriefSchema] = Field(default_factory=list, description="Organizations (via teams)")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# USER UPDATE SCHEMAS
# =============================================================================


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated full name")
    email: Optional[EmailStr] = Field(None, description="Updated email address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Mirko Siddi Updated"
            }
        }
    )


# =============================================================================
# GENERAL RESPONSE SCHEMAS
# =============================================================================


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str = Field(..., description="Error detail message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Invalid credentials"
            }
        }
    )
