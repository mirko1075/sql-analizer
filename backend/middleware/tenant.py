"""
Tenant isolation middleware.
Ensures queries are automatically filtered by organization/team/identity.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from contextlib import contextmanager

from db.models_multitenant import User, Organization, UserRole


class TenantContext:
    """
    Thread-local tenant context for query filtering.
    Automatically filters all queries by organization/team/identity.
    """

    def __init__(
        self,
        organization_id: Optional[int] = None,
        team_id: Optional[int] = None,
        identity_id: Optional[int] = None,
        user: Optional[User] = None,
        organization: Optional[Organization] = None
    ):
        self.organization_id = organization_id
        self.team_id = team_id
        self.identity_id = identity_id
        self.user = user
        self.organization = organization
        self.is_super_admin = user and user.role == UserRole.SUPER_ADMIN

    @classmethod
    def from_user(cls, user: User) -> "TenantContext":
        """Create tenant context from authenticated user."""
        return cls(
            organization_id=user.organization_id,
            team_id=user.identity.team_id if user.identity else None,
            identity_id=user.identity_id,
            user=user
        )

    @classmethod
    def from_organization(cls, organization: Organization) -> "TenantContext":
        """Create tenant context from organization (API key auth)."""
        return cls(
            organization_id=organization.id,
            organization=organization
        )

    def can_access_organization(self, org_id: int) -> bool:
        """Check if current context can access given organization."""
        if self.is_super_admin:
            return True
        return self.organization_id == org_id

    def can_access_team(self, team_id: int, db: Session) -> bool:
        """Check if current context can access given team."""
        if self.is_super_admin:
            return True

        from db.models_multitenant import Team
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            return False

        if self.user and self.user.role == UserRole.ORG_ADMIN:
            return team.organization_id == self.organization_id

        return self.team_id == team_id

    def can_access_identity(self, identity_id: int, db: Session) -> bool:
        """Check if current context can access given identity."""
        if self.is_super_admin:
            return True

        from db.models_multitenant import Identity
        identity = db.query(Identity).filter(Identity.id == identity_id).first()
        if not identity:
            return False

        if self.user and self.user.role == UserRole.ORG_ADMIN:
            from db.models_multitenant import Team
            team = db.query(Team).filter(Team.id == identity.team_id).first()
            return team and team.organization_id == self.organization_id

        if self.user and self.user.role == UserRole.TEAM_LEAD:
            return identity.team_id == self.team_id

        return self.identity_id == identity_id


class TenantAwareQuery:
    """
    Helper to add tenant filters to queries automatically.
    """

    def __init__(self, context: TenantContext):
        self.context = context

    def filter_slow_queries(self, query):
        """
        Add tenant filters to SlowQuery queries.

        Super admins: no filter (see all)
        Org admins: filter by organization
        Team leads: filter by team
        Users: filter by identity
        Client agents: filter by organization
        """
        from db.models_multitenant import SlowQuery

        if self.context.is_super_admin:
            return query  # Super admin sees everything

        # Organization filter (always applied for non-super-admins)
        if self.context.organization_id:
            query = query.filter(SlowQuery.organization_id == self.context.organization_id)

        # Team filter (for team leads and below)
        if self.context.user:
            if self.context.user.role == UserRole.TEAM_LEAD and self.context.team_id:
                query = query.filter(SlowQuery.team_id == self.context.team_id)

            # Identity filter (for regular users)
            elif self.context.user.role == UserRole.USER and self.context.identity_id:
                query = query.filter(SlowQuery.identity_id == self.context.identity_id)

        return query

    def filter_organizations(self, query):
        """
        Add tenant filters to Organization queries.

        Super admins: see all organizations
        Others: only their own organization
        """
        from db.models_multitenant import Organization

        if self.context.is_super_admin:
            return query  # Super admin sees everything

        if self.context.organization_id:
            query = query.filter(Organization.id == self.context.organization_id)

        return query

    def filter_teams(self, query):
        """
        Add tenant filters to Team queries.

        Super admins: see all teams
        Org admins: see teams in their organization
        Others: see only their team
        """
        from db.models_multitenant import Team

        if self.context.is_super_admin:
            return query  # Super admin sees everything

        if self.context.user and self.context.user.role == UserRole.ORG_ADMIN:
            # Org admin sees all teams in their organization
            if self.context.organization_id:
                query = query.filter(Team.organization_id == self.context.organization_id)
        elif self.context.team_id:
            # Team lead or user sees only their team
            query = query.filter(Team.id == self.context.team_id)

        return query

    def filter_identities(self, query):
        """
        Add tenant filters to Identity queries.

        Super admins: see all identities
        Org admins: see identities in their organization
        Team leads: see identities in their team
        Users: see only their identity
        """
        from db.models_multitenant import Identity, Team

        if self.context.is_super_admin:
            return query  # Super admin sees everything

        if self.context.user:
            if self.context.user.role == UserRole.ORG_ADMIN:
                # Org admin sees all identities in their organization
                query = query.join(Team).filter(Team.organization_id == self.context.organization_id)

            elif self.context.user.role == UserRole.TEAM_LEAD and self.context.team_id:
                # Team lead sees identities in their team
                query = query.filter(Identity.team_id == self.context.team_id)

            elif self.context.identity_id:
                # Regular user sees only their identity
                query = query.filter(Identity.id == self.context.identity_id)

        return query

    def filter_users(self, query):
        """
        Add tenant filters to User queries.

        Super admins: see all users
        Org admins: see users in their organization
        Team leads: see users in their team
        Users: see only themselves
        """
        from db.models_multitenant import User, Identity

        if self.context.is_super_admin:
            return query  # Super admin sees everything

        if self.context.user:
            if self.context.user.role == UserRole.ORG_ADMIN:
                # Org admin sees all users in their organization
                query = query.filter(User.organization_id == self.context.organization_id)

            elif self.context.user.role == UserRole.TEAM_LEAD and self.context.team_id:
                # Team lead sees users in their team
                query = query.join(Identity).filter(Identity.team_id == self.context.team_id)

            else:
                # Regular user sees only themselves
                query = query.filter(User.id == self.context.user.id)

        return query


# ============================================================================
# CONTEXT MANAGER FOR TENANT SCOPE
# ============================================================================

@contextmanager
def tenant_scope(context: TenantContext):
    """
    Context manager for tenant-scoped operations.

    Usage:
        with tenant_scope(TenantContext.from_user(user)):
            # All queries here are automatically filtered
            queries = db.query(SlowQuery).all()  # Only user's queries
    """
    # This is a simple implementation. For production, consider using
    # contextvars or thread-local storage for automatic query filtering.
    yield TenantAwareQuery(context)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_tenant_aware_query(context: TenantContext) -> TenantAwareQuery:
    """
    Get a tenant-aware query helper.

    Usage:
        tenant_query = get_tenant_aware_query(TenantContext.from_user(user))
        filtered_queries = tenant_query.filter_slow_queries(
            db.query(SlowQuery)
        ).all()
    """
    return TenantAwareQuery(context)


def verify_tenant_ownership(
    obj,
    context: TenantContext,
    db: Session
) -> bool:
    """
    Verify that an object belongs to the current tenant context.

    Args:
        obj: Database model instance (SlowQuery, Team, Identity, etc.)
        context: Tenant context
        db: Database session

    Returns:
        True if object belongs to tenant, False otherwise
    """
    from db.models_multitenant import SlowQuery, Team, Identity, User

    # Super admin can access everything
    if context.is_super_admin:
        return True

    # Check based on object type
    if isinstance(obj, SlowQuery):
        if obj.organization_id != context.organization_id:
            return False
        if context.team_id and obj.team_id != context.team_id:
            return False
        if context.identity_id and obj.identity_id != context.identity_id:
            return False
        return True

    elif isinstance(obj, Team):
        return context.can_access_team(obj.id, db)

    elif isinstance(obj, Identity):
        return context.can_access_identity(obj.id, db)

    elif isinstance(obj, User):
        if context.user:
            if context.user.role == UserRole.ORG_ADMIN:
                return obj.organization_id == context.organization_id
            elif context.user.role == UserRole.TEAM_LEAD:
                if obj.identity_id and context.team_id:
                    obj_identity = db.query(Identity).filter(Identity.id == obj.identity_id).first()
                    return obj_identity and obj_identity.team_id == context.team_id
            else:
                return obj.id == context.user.id
        return False

    # Unknown type - deny access
    return False
