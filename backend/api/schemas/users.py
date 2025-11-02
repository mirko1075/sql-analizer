"""
Pydantic schemas for user profile management.

Defines request and response models for user operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, EmailStr


# =============================================================================
# USER PROFILE SCHEMAS
# =============================================================================


class UserUpdateProfileRequest(BaseModel):
    """Request schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe Updated"
            }
        }
    )


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password."""
    current_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldSecurePassword123!",
                "new_password": "NewSecurePassword456!"
            }
        }
    )


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    is_active: bool = Field(..., description="User is active")
    is_superuser: bool = Field(..., description="User is superuser")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-11-01T08:00:00Z"
            }
        }
    )


class UserSessionResponse(BaseModel):
    """Response schema for user session."""
    token_type: str = Field(..., description="Token type: access or refresh")
    created_at: datetime = Field(..., description="Session creation timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    user_agent: Optional[str] = Field(None, description="User agent")
    ip_address: Optional[str] = Field(None, description="IP address")
    revoked: bool = Field(..., description="Session is revoked")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "token_type": "access",
                "created_at": "2025-11-01T10:00:00Z",
                "expires_at": "2025-11-01T10:30:00Z",
                "user_agent": "Mozilla/5.0...",
                "ip_address": "192.168.1.100",
                "revoked": False
            }
        }
    )


class UserSessionListResponse(BaseModel):
    """Response schema for list of user sessions."""
    total: int = Field(..., description="Total number of active sessions")
    sessions: List[UserSessionResponse] = Field(..., description="List of sessions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 2,
                "sessions": []
            }
        }
    )
