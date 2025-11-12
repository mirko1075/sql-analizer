"""
Admin routes: organization, team, identity, and user management.
Requires appropriate admin permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from db.models_multitenant import (
    User, Organization, Team, Identity,
    get_db, UserRole
)
from core.security import hash_password, is_strong_password
from middleware.auth import (
    get_current_user,
    require_super_admin,
    require_org_admin,
    check_organization_access
)
from middleware.tenant import TenantContext, get_tenant_aware_query

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

# Organizations
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    settings: Optional[dict] = {}


class OrganizationResponse(BaseModel):
    id: int
    name: str
    settings: dict
    api_key_created_at: Optional[datetime]
    api_key_expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    api_key: str
    organization_id: int
    expires_at: datetime
    message: str = "⚠️ Save this API key! It will not be shown again."


# Teams
class TeamCreate(BaseModel):
    organization_id: int
    name: str = Field(..., min_length=1, max_length=255)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class TeamResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Identities
class IdentityCreate(BaseModel):
    team_id: int
    name: str = Field(..., min_length=1, max_length=255)


class IdentityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class IdentityResponse(BaseModel):
    id: int
    team_id: int
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Users
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole
    organization_id: int
    identity_id: Optional[int] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    identity_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_id: int
    identity_id: Optional[int]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ORGANIZATION MANAGEMENT (Super Admin only)
# ============================================================================

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all organizations (Super Admin only).
    """
    orgs = db.query(Organization).offset(skip).limit(limit).all()
    return orgs


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new organization (Super Admin only).
    """
    # Check if organization name already exists
    existing_org = db.query(Organization).filter(Organization.name == org_data.name).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )

    # Create organization
    org = Organization(
        name=org_data.name,
        settings=org_data.settings or {}
    )
    db.add(org)
    db.flush()

    # Generate API key
    api_key = org.generate_api_key()
    db.commit()
    db.refresh(org)

    # Return organization details with API key (only shown once!)
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        settings=org.settings,
        api_key_created_at=org.api_key_created_at,
        api_key_expires_at=org.api_key_expires_at,
        created_at=org.created_at,
        updated_at=org.updated_at
    )


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get organization details (Super Admin only).
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org


@router.post("/organizations/{org_id}/regenerate-api-key", response_model=APIKeyResponse)
async def regenerate_api_key(
    org_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Regenerate API key for an organization (Super Admin only).

    ⚠️ This will invalidate the old API key!
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Generate new API key
    api_key = org.generate_api_key()
    db.commit()

    return APIKeyResponse(
        api_key=api_key,
        organization_id=org.id,
        expires_at=org.api_key_expires_at
    )


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete an organization (Super Admin only).

    ⚠️ This will cascade delete all teams, identities, users, and queries!
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Don't allow deleting system organization
    if org.settings.get("is_system_org"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system organization"
        )

    db.delete(org)
    db.commit()
    return None


# ============================================================================
# TEAM MANAGEMENT (Org Admin and above)
# ============================================================================

@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    organization_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List teams (filtered by user permissions).

    - Super Admin: all teams (or filtered by organization_id)
    - Org Admin: teams in their organization
    - Team Lead/User: their own team only
    """
    context = TenantContext.from_user(current_user)
    tenant_query = get_tenant_aware_query(context)

    query = db.query(Team)

    # Apply organization filter if specified (super admin only)
    if organization_id and current_user.role == UserRole.SUPER_ADMIN:
        query = query.filter(Team.organization_id == organization_id)

    # Apply tenant filtering
    query = tenant_query.filter_teams(query)

    teams = query.offset(skip).limit(limit).all()
    return teams


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new team (Org Admin or Super Admin).
    """
    # Check organization access
    check_organization_access(current_user, team_data.organization_id)

    # Check if team name already exists in organization
    existing_team = db.query(Team).filter(
        Team.organization_id == team_data.organization_id,
        Team.name == team_data.name
    ).first()

    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already exists in this organization"
        )

    # Create team
    team = Team(
        organization_id=team_data.organization_id,
        name=team_data.name
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    return team


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Update a team (Org Admin or Super Admin).
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check organization access
    check_organization_access(current_user, team.organization_id)

    # Update fields
    if team_data.name:
        # Check for duplicate name
        existing = db.query(Team).filter(
            Team.organization_id == team.organization_id,
            Team.name == team_data.name,
            Team.id != team_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team name already exists"
            )
        team.name = team_data.name

    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a team (Org Admin or Super Admin).

    ⚠️ This will cascade delete all identities, users, and queries in the team!
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    check_organization_access(current_user, team.organization_id)

    db.delete(team)
    db.commit()
    return None


# ============================================================================
# IDENTITY MANAGEMENT (Org Admin and above)
# ============================================================================

@router.get("/identities", response_model=List[IdentityResponse])
async def list_identities(
    team_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List identities (filtered by user permissions).
    """
    context = TenantContext.from_user(current_user)
    tenant_query = get_tenant_aware_query(context)

    query = db.query(Identity)

    # Apply team filter if specified
    if team_id:
        query = query.filter(Identity.team_id == team_id)

    # Apply tenant filtering
    query = tenant_query.filter_identities(query)

    identities = query.offset(skip).limit(limit).all()
    return identities


@router.post("/identities", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
async def create_identity(
    identity_data: IdentityCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new identity (Org Admin or Super Admin).
    """
    # Get team and check organization access
    team = db.query(Team).filter(Team.id == identity_data.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    check_organization_access(current_user, team.organization_id)

    # Check for duplicate name
    existing = db.query(Identity).filter(
        Identity.team_id == identity_data.team_id,
        Identity.name == identity_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity name already exists in this team"
        )

    # Create identity
    identity = Identity(
        team_id=identity_data.team_id,
        name=identity_data.name
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)

    return identity


@router.delete("/identities/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_identity(
    identity_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Delete an identity (Org Admin or Super Admin).

    ⚠️ This will cascade delete all users and queries in the identity!
    """
    identity = db.query(Identity).filter(Identity.id == identity_id).first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    # Check organization access via team
    team = db.query(Team).filter(Team.id == identity.team_id).first()
    if team:
        check_organization_access(current_user, team.organization_id)

    db.delete(identity)
    db.commit()
    return None


# ============================================================================
# USER MANAGEMENT (Org Admin and above)
# ============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    organization_id: Optional[int] = None,
    team_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List users (filtered by user permissions).
    """
    context = TenantContext.from_user(current_user)
    tenant_query = get_tenant_aware_query(context)

    query = db.query(User)

    # Apply filters if specified (super admin only)
    if current_user.role == UserRole.SUPER_ADMIN:
        if organization_id:
            query = query.filter(User.organization_id == organization_id)

    # Apply tenant filtering
    query = tenant_query.filter_users(query)

    users = query.offset(skip).limit(limit).all()

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            organization_id=u.organization_id,
            identity_id=u.identity_id,
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Org Admin or Super Admin).
    """
    # Check organization access
    check_organization_access(current_user, user_data.organization_id)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check password strength
    is_strong, error_msg = is_strong_password(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Org admins cannot create super admins
    if current_user.role == UserRole.ORG_ADMIN and user_data.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create super admin users"
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        organization_id=user_data.organization_id,
        identity_id=user_data.identity_id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        organization_id=user.organization_id,
        identity_id=user.identity_id,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Update a user (Org Admin or Super Admin).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check organization access
    check_organization_access(current_user, user.organization_id)

    # Org admins cannot modify super admins
    if current_user.role == UserRole.ORG_ADMIN and user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify super admin users"
        )

    # Update fields
    if user_data.email:
        # Check for duplicate email
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.role and current_user.role == UserRole.SUPER_ADMIN:
        user.role = user_data.role

    if user_data.identity_id is not None:
        user.identity_id = user_data.identity_id

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        organization_id=user.organization_id,
        identity_id=user.identity_id,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user (Org Admin or Super Admin).

    Cannot delete yourself or super admins (unless you're a super admin).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    check_organization_access(current_user, user.organization_id)

    # Org admins cannot delete super admins
    if current_user.role == UserRole.ORG_ADMIN and user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete super admin users"
        )

    db.delete(user)
    db.commit()
    return None
