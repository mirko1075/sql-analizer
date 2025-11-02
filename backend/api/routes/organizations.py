"""
Organizations API routes.

Handles organization CRUD operations.
Note: Most users will only interact with their organization via teams.
This is mainly for admin purposes.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_active_user
from backend.db.models import User, Organization, Team, TeamMember
from backend.api.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationBriefResponse,
    OrganizationDetailResponse,
    OrganizationListResponse,
)
from backend.api.schemas.auth import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organizations"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_organization_or_404(org_id: UUID, db: Session) -> Organization:
    """Get organization by ID or raise 404."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )
    return org


def user_belongs_to_organization(user_id: UUID, org_id: UUID, db: Session) -> bool:
    """Check if user belongs to any team in the organization."""
    membership = db.query(TeamMember).join(
        Team, TeamMember.team_id == Team.id
    ).filter(
        TeamMember.user_id == user_id,
        Team.organization_id == org_id
    ).first()

    return membership is not None


# =============================================================================
# LIST ORGANIZATIONS
# =============================================================================


@router.get(
    "",
    response_model=OrganizationListResponse,
    summary="List user's organizations",
    description="Get all organizations the current user belongs to"
)
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all organizations the current user has access to.

    Returns organizations where user is member of at least one team.
    """
    try:
        # Get organizations via team memberships
        org_ids = db.query(Team.organization_id).join(
            TeamMember, Team.id == TeamMember.team_id
        ).filter(
            TeamMember.user_id == current_user.id
        ).distinct().all()

        org_ids = [org_id for (org_id,) in org_ids]

        # Get organization details
        organizations = db.query(Organization).filter(
            Organization.id.in_(org_ids)
        ).all()

        orgs_data = []
        for org in organizations:
            # Get team count
            team_count = db.query(func.count(Team.id)).filter(
                Team.organization_id == org.id
            ).scalar() or 0

            orgs_data.append(OrganizationBriefResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                plan_type=org.plan_type,
                is_active=org.is_active,
                team_count=team_count
            ))

        return OrganizationListResponse(
            total=len(orgs_data),
            organizations=orgs_data
        )

    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list organizations"
        )


# =============================================================================
# GET ORGANIZATION DETAILS
# =============================================================================


@router.get(
    "/{org_id}",
    response_model=OrganizationDetailResponse,
    summary="Get organization details",
    description="Get detailed information about an organization"
)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about an organization.

    User must belong to at least one team in the organization.
    """
    try:
        org = get_organization_or_404(org_id, db)

        # Verify user has access
        if not user_belongs_to_organization(current_user.id, org_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization"
            )

        # Get team count
        team_count = db.query(func.count(Team.id)).filter(
            Team.organization_id == org.id
        ).scalar() or 0

        return OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            plan_type=org.plan_type,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            team_count=team_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


# =============================================================================
# CREATE ORGANIZATION (Superuser only)
# =============================================================================


@router.post(
    "",
    response_model=OrganizationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization (superuser only)"
)
async def create_organization(
    request: OrganizationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new organization.

    Requires superuser privileges.
    Regular users get an organization automatically on registration.
    """
    try:
        # Check superuser
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can create organizations"
            )

        # Check slug uniqueness
        existing = db.query(Organization).filter(
            Organization.slug == request.slug
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization with slug '{request.slug}' already exists"
            )

        # Create organization
        new_org = Organization(
            name=request.name,
            slug=request.slug,
            description=request.description,
            plan_type='FREE',  # Default to FREE
            is_active=True
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        logger.info(f"Superuser {current_user.email} created organization '{new_org.name}'")

        return OrganizationDetailResponse(
            id=new_org.id,
            name=new_org.name,
            slug=new_org.slug,
            description=new_org.description,
            plan_type=new_org.plan_type,
            is_active=new_org.is_active,
            created_at=new_org.created_at,
            updated_at=new_org.updated_at,
            team_count=0
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


# =============================================================================
# UPDATE ORGANIZATION (Superuser only)
# =============================================================================


@router.put(
    "/{org_id}",
    response_model=OrganizationDetailResponse,
    summary="Update organization",
    description="Update organization details (superuser only)"
)
async def update_organization(
    org_id: UUID,
    request: OrganizationUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update organization information.

    Requires superuser privileges.
    """
    try:
        # Check superuser
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can update organizations"
            )

        org = get_organization_or_404(org_id, db)

        # Update fields
        if request.name is not None:
            org.name = request.name
        if request.description is not None:
            org.description = request.description
        if request.is_active is not None:
            org.is_active = request.is_active

        db.commit()
        db.refresh(org)

        logger.info(f"Superuser {current_user.email} updated organization '{org.name}'")

        # Get team count
        team_count = db.query(func.count(Team.id)).filter(
            Team.organization_id == org.id
        ).scalar() or 0

        return OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            plan_type=org.plan_type,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            team_count=team_count
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


# =============================================================================
# DELETE ORGANIZATION (Superuser only)
# =============================================================================


@router.delete(
    "/{org_id}",
    response_model=MessageResponse,
    summary="Delete organization",
    description="Delete an organization (superuser only)"
)
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an organization.

    Requires superuser privileges.
    This will cascade delete all teams in the organization.
    """
    try:
        # Check superuser
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can delete organizations"
            )

        org = get_organization_or_404(org_id, db)

        org_name = org.name
        db.delete(org)
        db.commit()

        logger.warning(
            f"Superuser {current_user.email} deleted organization '{org_name}'"
        )

        return MessageResponse(
            message=f"Organization '{org_name}' deleted successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )
