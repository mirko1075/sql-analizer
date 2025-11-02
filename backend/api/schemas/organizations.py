"""
Pydantic schemas for organizations API.

Defines request and response models for organization management.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ORGANIZATION SCHEMAS
# =============================================================================


class OrganizationCreateRequest(BaseModel):
    """Request schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="Organization slug (URL-friendly)")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "description": "Enterprise software development company"
            }
        }
    )


class OrganizationUpdateRequest(BaseModel):
    """Request schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")
    is_active: Optional[bool] = Field(None, description="Organization active status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corporation Updated",
                "description": "Updated description",
                "is_active": True
            }
        }
    )


class OrganizationBriefResponse(BaseModel):
    """Brief organization information."""
    id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="Organization slug")
    plan_type: str = Field(..., description="Plan type: FREE, PRO, ENTERPRISE")
    is_active: bool = Field(..., description="Organization is active")
    team_count: Optional[int] = Field(None, description="Number of teams")

    model_config = ConfigDict(from_attributes=True)


class OrganizationDetailResponse(BaseModel):
    """Detailed organization information."""
    id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="Organization slug")
    description: Optional[str] = Field(None, description="Organization description")
    plan_type: str = Field(..., description="Plan type: FREE, PRO, ENTERPRISE")
    is_active: bool = Field(..., description="Organization is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    team_count: int = Field(..., description="Number of teams")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "description": "Enterprise software development",
                "plan_type": "PRO",
                "is_active": True,
                "created_at": "2025-11-01T08:00:00Z",
                "updated_at": "2025-11-01T10:30:00Z",
                "team_count": 5
            }
        }
    )


class OrganizationListResponse(BaseModel):
    """Response schema for list of organizations."""
    total: int = Field(..., description="Total number of organizations")
    organizations: List[OrganizationBriefResponse] = Field(..., description="List of organizations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 1,
                "organizations": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Acme Corporation",
                        "slug": "acme-corp",
                        "plan_type": "PRO",
                        "is_active": True,
                        "team_count": 5
                    }
                ]
            }
        }
    )
