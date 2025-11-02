"""
Teams API routes.

Handles team CRUD operations and member management.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_active_user, require_role
from backend.db.models import User, Team, TeamMember, Organization
from backend.api.schemas.teams import (
    TeamCreateRequest,
    TeamUpdateRequest,
    TeamBriefResponse,
    TeamDetailResponse,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberListResponse,
    AddTeamMemberRequest,
    UpdateTeamMemberRequest,
)
from backend.api.schemas.auth import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/teams", tags=["Teams"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_team_or_404(team_id: UUID, db: Session) -> Team:
    """Get team by ID or raise 404."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    return team


def get_user_role_in_team(user_id: UUID, team_id: UUID, db: Session) -> str:
    """Get user's role in a team, or None if not a member."""
    membership = db.query(TeamMember).filter(
        TeamMember.user_id == user_id,
        TeamMember.team_id == team_id
    ).first()
    return membership.role if membership else None


def require_team_role(team_id: UUID, allowed_roles: List[str], current_user: User, db: Session):
    """
    Check if current user has one of the allowed roles in the team.
    Raises HTTPException if not.
    """
    user_role = get_user_role_in_team(current_user.id, team_id, db)

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team"
        )

    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(allowed_roles)}. You have: {user_role}"
        )


# =============================================================================
# LIST TEAMS
# =============================================================================


@router.get(
    "",
    response_model=TeamListResponse,
    summary="List user's teams",
    description="Get all teams the current user is a member of"
)
async def list_teams(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all teams the current user belongs to.

    Returns teams with member count and user's role in each team.
    """
    try:
        # Get user's team memberships with team details
        memberships = db.query(TeamMember, Team).join(
            Team, TeamMember.team_id == Team.id
        ).filter(
            TeamMember.user_id == current_user.id
        ).all()

        teams_data = []
        for membership, team in memberships:
            # Get member count for this team
            member_count = db.query(func.count(TeamMember.user_id)).filter(
                TeamMember.team_id == team.id
            ).scalar() or 0

            teams_data.append(TeamBriefResponse(
                id=team.id,
                name=team.name,
                organization_id=team.organization_id,
                is_active=team.is_active,
                member_count=member_count,
                user_role=membership.role
            ))

        return TeamListResponse(
            total=len(teams_data),
            teams=teams_data
        )

    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list teams"
        )


# =============================================================================
# CREATE TEAM
# =============================================================================


@router.post(
    "",
    response_model=TeamDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create team",
    description="Create a new team in the user's organization"
)
async def create_team(
    request: TeamCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new team.

    - User must belong to an organization
    - User becomes OWNER of the new team
    - Team is created within user's first organization
    """
    try:
        # Get user's first organization (from their first team membership)
        user_membership = db.query(TeamMember, Team).join(
            Team, TeamMember.team_id == Team.id
        ).filter(
            TeamMember.user_id == current_user.id
        ).first()

        if not user_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must belong to an organization to create a team"
            )

        _, first_team = user_membership
        organization_id = first_team.organization_id

        # Check if team name already exists in this organization
        existing = db.query(Team).filter(
            Team.organization_id == organization_id,
            Team.name == request.name
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{request.name}' already exists in this organization"
            )

        # Create team
        new_team = Team(
            organization_id=organization_id,
            name=request.name,
            description=request.description,
            is_active=True
        )
        db.add(new_team)
        db.flush()

        # Add creator as OWNER
        team_member = TeamMember(
            team_id=new_team.id,
            user_id=current_user.id,
            role='OWNER'
        )
        db.add(team_member)
        db.commit()
        db.refresh(new_team)

        logger.info(f"User {current_user.email} created team '{new_team.name}'")

        # Build response with member details
        members = db.query(TeamMember, User).join(
            User, TeamMember.user_id == User.id
        ).filter(
            TeamMember.team_id == new_team.id
        ).all()

        members_data = [
            TeamMemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=membership.role,
                joined_at=membership.joined_at
            )
            for membership, user in members
        ]

        return TeamDetailResponse(
            id=new_team.id,
            organization_id=new_team.organization_id,
            name=new_team.name,
            description=new_team.description,
            is_active=new_team.is_active,
            created_at=new_team.created_at,
            updated_at=new_team.updated_at,
            member_count=len(members_data),
            members=members_data
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team"
        )


# =============================================================================
# GET TEAM DETAILS
# =============================================================================


@router.get(
    "/{team_id}",
    response_model=TeamDetailResponse,
    summary="Get team details",
    description="Get detailed information about a specific team"
)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a team.

    User must be a member of the team.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Verify user is a member
        user_role = get_user_role_in_team(current_user.id, team_id, db)
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )

        # Get team members
        members = db.query(TeamMember, User).join(
            User, TeamMember.user_id == User.id
        ).filter(
            TeamMember.team_id == team_id
        ).all()

        members_data = [
            TeamMemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=membership.role,
                joined_at=membership.joined_at
            )
            for membership, user in members
        ]

        return TeamDetailResponse(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            description=team.description,
            is_active=team.is_active,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=len(members_data),
            members=members_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team"
        )


# =============================================================================
# UPDATE TEAM
# =============================================================================


@router.put(
    "/{team_id}",
    response_model=TeamDetailResponse,
    summary="Update team",
    description="Update team details (requires OWNER or ADMIN role)"
)
async def update_team(
    team_id: UUID,
    request: TeamUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update team information.

    Requires OWNER or ADMIN role in the team.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Check user has required role
        require_team_role(team_id, ["OWNER", "ADMIN"], current_user, db)

        # Check name uniqueness if updating name
        if request.name and request.name != team.name:
            existing = db.query(Team).filter(
                Team.organization_id == team.organization_id,
                Team.name == request.name,
                Team.id != team_id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team with name '{request.name}' already exists in this organization"
                )

        # Update fields
        if request.name is not None:
            team.name = request.name
        if request.description is not None:
            team.description = request.description
        if request.is_active is not None:
            team.is_active = request.is_active

        db.commit()
        db.refresh(team)

        logger.info(f"User {current_user.email} updated team '{team.name}'")

        # Get members for response
        members = db.query(TeamMember, User).join(
            User, TeamMember.user_id == User.id
        ).filter(
            TeamMember.team_id == team_id
        ).all()

        members_data = [
            TeamMemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=membership.role,
                joined_at=membership.joined_at
            )
            for membership, user in members
        ]

        return TeamDetailResponse(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            description=team.description,
            is_active=team.is_active,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=len(members_data),
            members=members_data
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team"
        )


# =============================================================================
# DELETE TEAM
# =============================================================================


@router.delete(
    "/{team_id}",
    response_model=MessageResponse,
    summary="Delete team",
    description="Delete a team (requires OWNER role)"
)
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a team.

    Requires OWNER role. This will cascade delete all team memberships
    and set team_id to NULL for associated slow queries.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Check user is OWNER
        require_team_role(team_id, ["OWNER"], current_user, db)

        team_name = team.name
        db.delete(team)
        db.commit()

        logger.info(f"User {current_user.email} deleted team '{team_name}'")

        return MessageResponse(
            message=f"Team '{team_name}' deleted successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team"
        )


# =============================================================================
# TEAM MEMBERS MANAGEMENT
# =============================================================================


@router.get(
    "/{team_id}/members",
    response_model=TeamMemberListResponse,
    summary="List team members",
    description="Get all members of a team"
)
async def list_team_members(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all members of a team.

    User must be a member of the team.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Verify user is a member
        user_role = get_user_role_in_team(current_user.id, team_id, db)
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )

        # Get members
        members = db.query(TeamMember, User).join(
            User, TeamMember.user_id == User.id
        ).filter(
            TeamMember.team_id == team_id
        ).order_by(TeamMember.role, User.email).all()

        members_data = [
            TeamMemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=membership.role,
                joined_at=membership.joined_at
            )
            for membership, user in members
        ]

        return TeamMemberListResponse(
            team_id=team.id,
            team_name=team.name,
            total=len(members_data),
            members=members_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing team members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list team members"
        )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description="Add a new member to the team (requires OWNER or ADMIN role)"
)
async def add_team_member(
    team_id: UUID,
    request: AddTeamMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a new member to the team.

    Requires OWNER or ADMIN role.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Check user has required role
        require_team_role(team_id, ["OWNER", "ADMIN"], current_user, db)

        # Find user by email
        new_user = db.query(User).filter(User.email == request.user_email).first()
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{request.user_email}' not found"
            )

        # Check if user is already a member
        existing_membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == new_user.id
        ).first()

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{request.user_email}' is already a member of this team"
            )

        # Validate role
        valid_roles = ["OWNER", "ADMIN", "MEMBER", "VIEWER"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

        # Add member
        new_membership = TeamMember(
            team_id=team_id,
            user_id=new_user.id,
            role=request.role
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)

        logger.info(
            f"User {current_user.email} added {new_user.email} to team '{team.name}' "
            f"with role {request.role}"
        )

        return TeamMemberResponse(
            user_id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_membership.role,
            joined_at=new_membership.joined_at
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member"
        )


@router.put(
    "/{team_id}/members/{user_id}",
    response_model=TeamMemberResponse,
    summary="Update member role",
    description="Update a team member's role (requires OWNER role)"
)
async def update_team_member_role(
    team_id: UUID,
    user_id: UUID,
    request: UpdateTeamMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a team member's role.

    Requires OWNER role. Cannot modify your own role.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Check user is OWNER
        require_team_role(team_id, ["OWNER"], current_user, db)

        # Cannot modify own role
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot modify your own role"
            )

        # Get membership
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this team"
            )

        # Validate role
        valid_roles = ["OWNER", "ADMIN", "MEMBER", "VIEWER"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

        # Update role
        old_role = membership.role
        membership.role = request.role
        db.commit()
        db.refresh(membership)

        # Get user for response
        user = db.query(User).filter(User.id == user_id).first()

        logger.info(
            f"User {current_user.email} changed role of {user.email} in team '{team.name}' "
            f"from {old_role} to {request.role}"
        )

        return TeamMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team member role"
        )


@router.delete(
    "/{team_id}/members/{user_id}",
    response_model=MessageResponse,
    summary="Remove team member",
    description="Remove a member from the team (requires OWNER or ADMIN role)"
)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a member from the team.

    Requires OWNER or ADMIN role. Cannot remove the last OWNER.
    """
    try:
        team = get_team_or_404(team_id, db)

        # Check user has required role
        require_team_role(team_id, ["OWNER", "ADMIN"], current_user, db)

        # Get membership
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this team"
            )

        # Cannot remove yourself
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove yourself from the team"
            )

        # If removing an OWNER, check that there's at least one other OWNER
        if membership.role == "OWNER":
            owner_count = db.query(func.count(TeamMember.user_id)).filter(
                TeamMember.team_id == team_id,
                TeamMember.role == "OWNER"
            ).scalar() or 0

            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last OWNER from the team"
                )

        # Get user for logging
        user = db.query(User).filter(User.id == user_id).first()

        db.delete(membership)
        db.commit()

        logger.info(
            f"User {current_user.email} removed {user.email} from team '{team.name}'"
        )

        return MessageResponse(
            message=f"User '{user.email}' removed from team successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member"
        )
