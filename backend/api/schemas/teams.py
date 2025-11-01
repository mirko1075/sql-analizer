"""
Pydantic schemas for teams API.

Defines request and response models for team management.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# TEAM MEMBER SCHEMAS
# =============================================================================


class TeamMemberResponse(BaseModel):
    """Response schema for team member."""
    user_id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="Role in team: OWNER, ADMIN, MEMBER, VIEWER")
    joined_at: datetime = Field(..., description="When user joined the team")

    model_config = ConfigDict(from_attributes=True)


class AddTeamMemberRequest(BaseModel):
    """Request schema for adding a team member."""
    user_email: str = Field(..., description="Email of user to add")
    role: str = Field(default="MEMBER", description="Role: OWNER, ADMIN, MEMBER, VIEWER")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_email": "john.doe@example.com",
                "role": "MEMBER"
            }
        }
    )


class UpdateTeamMemberRequest(BaseModel):
    """Request schema for updating a team member's role."""
    role: str = Field(..., description="New role: OWNER, ADMIN, MEMBER, VIEWER")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "ADMIN"
            }
        }
    )


# =============================================================================
# TEAM SCHEMAS
# =============================================================================


class TeamCreateRequest(BaseModel):
    """Request schema for creating a team."""
    name: str = Field(..., min_length=1, max_length=255, description="Team name")
    description: Optional[str] = Field(None, max_length=500, description="Team description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Backend Team",
                "description": "Team responsible for backend services"
            }
        }
    )


class TeamUpdateRequest(BaseModel):
    """Request schema for updating a team."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Team name")
    description: Optional[str] = Field(None, max_length=500, description="Team description")
    is_active: Optional[bool] = Field(None, description="Team active status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Backend Engineering Team",
                "description": "Updated description",
                "is_active": True
            }
        }
    )


class TeamBriefResponse(BaseModel):
    """Brief team information (for lists)."""
    id: UUID = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    organization_id: UUID = Field(..., description="Organization ID")
    is_active: bool = Field(..., description="Team is active")
    member_count: Optional[int] = Field(None, description="Number of members")
    user_role: Optional[str] = Field(None, description="Current user's role in this team")

    model_config = ConfigDict(from_attributes=True)


class TeamDetailResponse(BaseModel):
    """Detailed team information."""
    id: UUID = Field(..., description="Team ID")
    organization_id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    is_active: bool = Field(..., description="Team is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    member_count: int = Field(..., description="Number of members")
    members: List[TeamMemberResponse] = Field(default_factory=list, description="Team members")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "organization_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Backend Team",
                "description": "Team for backend development",
                "is_active": True,
                "created_at": "2025-11-01T08:00:00Z",
                "updated_at": "2025-11-01T10:30:00Z",
                "member_count": 5,
                "members": []
            }
        }
    )


class TeamListResponse(BaseModel):
    """Response schema for list of teams."""
    total: int = Field(..., description="Total number of teams")
    teams: List[TeamBriefResponse] = Field(..., description="List of teams")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 3,
                "teams": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Backend Team",
                        "organization_id": "660e8400-e29b-41d4-a716-446655440001",
                        "is_active": True,
                        "member_count": 5,
                        "user_role": "OWNER"
                    }
                ]
            }
        }
    )


class TeamMemberListResponse(BaseModel):
    """Response schema for list of team members."""
    team_id: UUID = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    total: int = Field(..., description="Total number of members")
    members: List[TeamMemberResponse] = Field(..., description="List of members")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "team_id": "550e8400-e29b-41d4-a716-446655440000",
                "team_name": "Backend Team",
                "total": 5,
                "members": [
                    {
                        "user_id": "770e8400-e29b-41d4-a716-446655440002",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "role": "OWNER",
                        "joined_at": "2025-11-01T08:00:00Z"
                    }
                ]
            }
        }
    )
