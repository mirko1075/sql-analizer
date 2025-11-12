"""
Tests for tenant isolation and RBAC middleware.
"""
import pytest

from db.models_multitenant import User, Organization, Team, Identity, SlowQuery, UserRole, QueryStatus
from middleware.tenant import (
    TenantContext,
    TenantAwareQuery,
    get_tenant_aware_query,
    verify_tenant_ownership
)


class TestTenantContext:
    """Tests for TenantContext."""

    def test_create_context_from_user(self, sample_user):
        """Test creating tenant context from user."""
        context = TenantContext.from_user(sample_user)

        assert context.organization_id == sample_user.organization_id
        assert context.identity_id == sample_user.identity_id
        assert context.user == sample_user
        assert context.is_super_admin is False

    def test_create_context_from_super_admin(self, sample_super_admin):
        """Test creating context from super admin."""
        context = TenantContext.from_user(sample_super_admin)

        assert context.is_super_admin is True

    def test_create_context_from_organization(self, sample_organization):
        """Test creating context from organization (API key auth)."""
        context = TenantContext.from_organization(sample_organization)

        assert context.organization_id == sample_organization.id
        assert context.organization == sample_organization
        assert context.user is None

    def test_can_access_organization(self, sample_user, sample_organization, second_organization):
        """Test organization access control."""
        context = TenantContext.from_user(sample_user)

        # Can access own organization
        assert context.can_access_organization(sample_organization.id) is True

        # Cannot access other organization
        assert context.can_access_organization(second_organization.id) is False

    def test_super_admin_can_access_all_organizations(self, sample_super_admin, second_organization):
        """Test that super admin can access all organizations."""
        context = TenantContext.from_user(sample_super_admin)

        assert context.can_access_organization(second_organization.id) is True


class TestTenantAwareQuery:
    """Tests for TenantAwareQuery filtering."""

    def test_filter_slow_queries_regular_user(
        self,
        db_session,
        sample_user,
        sample_organization,
        sample_team,
        sample_identity
    ):
        """Test that regular users only see their identity's queries."""
        # Create queries in user's identity
        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )

        # Create query in different identity (same org)
        other_identity = Identity(team_id=sample_team.id, name="Other Identity")
        db_session.add(other_identity)
        db_session.flush()

        query2 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=other_identity.id,
            sql_text="SELECT 2",
            sql_fingerprint="hash2",
            query_time=2.0
        )

        db_session.add_all([query1, query2])
        db_session.commit()

        # Query with tenant filtering
        context = TenantContext.from_user(sample_user)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_slow_queries(db_session.query(SlowQuery)).all()

        assert len(filtered) == 1
        assert filtered[0].identity_id == sample_identity.id

    def test_filter_slow_queries_org_admin(
        self,
        db_session,
        sample_org_admin,
        sample_organization,
        sample_team,
        sample_identity,
        second_organization,
        second_team,
        second_identity
    ):
        """Test that org admins see all queries in their organization."""
        # Create query in their org
        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )

        # Create query in other org
        query2 = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT 2",
            sql_fingerprint="hash2",
            query_time=2.0
        )

        db_session.add_all([query1, query2])
        db_session.commit()

        # Query with tenant filtering
        context = TenantContext.from_user(sample_org_admin)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_slow_queries(db_session.query(SlowQuery)).all()

        assert len(filtered) == 1
        assert filtered[0].organization_id == sample_organization.id

    def test_filter_slow_queries_super_admin(
        self,
        db_session,
        sample_super_admin,
        sample_organization,
        sample_team,
        sample_identity,
        second_organization,
        second_team,
        second_identity
    ):
        """Test that super admins see all queries."""
        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )

        query2 = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT 2",
            sql_fingerprint="hash2",
            query_time=2.0
        )

        db_session.add_all([query1, query2])
        db_session.commit()

        # Super admin sees everything
        context = TenantContext.from_user(sample_super_admin)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_slow_queries(db_session.query(SlowQuery)).all()

        assert len(filtered) == 2

    def test_filter_organizations(
        self,
        db_session,
        sample_user,
        sample_organization,
        second_organization
    ):
        """Test organization filtering."""
        context = TenantContext.from_user(sample_user)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_organizations(db_session.query(Organization)).all()

        assert len(filtered) == 1
        assert filtered[0].id == sample_organization.id

    def test_filter_teams_org_admin(
        self,
        db_session,
        sample_org_admin,
        sample_organization,
        sample_team,
        second_organization,
        second_team
    ):
        """Test that org admins see all teams in their organization."""
        # Create another team in same org
        team2 = Team(organization_id=sample_organization.id, name="Team 2")
        db_session.add(team2)
        db_session.commit()

        context = TenantContext.from_user(sample_org_admin)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_teams(db_session.query(Team)).all()

        assert len(filtered) == 2
        for team in filtered:
            assert team.organization_id == sample_organization.id

    def test_filter_users(
        self,
        db_session,
        sample_org_admin,
        sample_user,
        second_org_user
    ):
        """Test user filtering by organization."""
        context = TenantContext.from_user(sample_org_admin)
        tenant_query = get_tenant_aware_query(context)

        filtered = tenant_query.filter_users(db_session.query(User)).all()

        # Should see users in their org only
        org_ids = [u.organization_id for u in filtered]
        assert all(org_id == sample_org_admin.organization_id for org_id in org_ids)


class TestVerifyTenantOwnership:
    """Tests for tenant ownership verification."""

    def test_verify_slow_query_ownership_valid(
        self,
        db_session,
        sample_user,
        sample_organization,
        sample_team,
        sample_identity
    ):
        """Test verification with valid ownership."""
        query = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )
        db_session.add(query)
        db_session.commit()

        context = TenantContext.from_user(sample_user)

        assert verify_tenant_ownership(query, context, db_session) is True

    def test_verify_slow_query_ownership_invalid(
        self,
        db_session,
        sample_user,
        second_organization,
        second_team,
        second_identity
    ):
        """Test verification with invalid ownership (different org)."""
        query = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )
        db_session.add(query)
        db_session.commit()

        context = TenantContext.from_user(sample_user)

        assert verify_tenant_ownership(query, context, db_session) is False

    def test_super_admin_owns_everything(
        self,
        db_session,
        sample_super_admin,
        second_organization,
        second_team,
        second_identity
    ):
        """Test that super admin can access any resource."""
        query = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT 1",
            sql_fingerprint="hash1",
            query_time=1.0
        )
        db_session.add(query)
        db_session.commit()

        context = TenantContext.from_user(sample_super_admin)

        assert verify_tenant_ownership(query, context, db_session) is True


class TestRoleBasedAccess:
    """Tests for role-based access control logic."""

    def test_user_roles_hierarchy(self):
        """Test that user roles are properly defined."""
        assert UserRole.USER.value == "user"
        assert UserRole.TEAM_LEAD.value == "team_lead"
        assert UserRole.ORG_ADMIN.value == "org_admin"
        assert UserRole.SUPER_ADMIN.value == "super_admin"

    def test_context_access_levels_user(self, sample_user, db_session):
        """Test access levels for regular user."""
        context = TenantContext.from_user(sample_user)

        # User can access their org
        assert context.can_access_organization(sample_user.organization_id) is True

        # User can access their team (through identity)
        assert context.can_access_team(sample_user.identity.team_id, db_session) is True

        # User can access their identity
        assert context.can_access_identity(sample_user.identity_id, db_session) is True

    def test_context_access_levels_org_admin(
        self,
        sample_org_admin,
        sample_organization,
        db_session
    ):
        """Test access levels for org admin."""
        context = TenantContext.from_user(sample_org_admin)

        # Org admin can access their org
        assert context.can_access_organization(sample_organization.id) is True

        # Create team in their org
        team = Team(organization_id=sample_organization.id, name="Test Team")
        db_session.add(team)
        db_session.commit()

        # Org admin can access teams in their org
        assert context.can_access_team(team.id, db_session) is True

    def test_context_access_levels_super_admin(
        self,
        sample_super_admin,
        second_organization,
        second_team,
        second_identity,
        db_session
    ):
        """Test that super admin can access everything."""
        context = TenantContext.from_user(sample_super_admin)

        # Super admin can access any org
        assert context.can_access_organization(second_organization.id) is True

        # Super admin can access any team
        assert context.can_access_team(second_team.id, db_session) is True

        # Super admin can access any identity
        assert context.can_access_identity(second_identity.id, db_session) is True


class TestMultiTenantDataLeakPrevention:
    """Security tests to ensure no data leaks between tenants."""

    def test_no_cross_tenant_query_access(
        self,
        db_session,
        sample_user,
        sample_organization,
        sample_team,
        sample_identity,
        second_org_user,
        second_organization,
        second_team,
        second_identity
    ):
        """Test that users cannot access queries from other organizations."""
        # Create query in org 1
        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT secret_data_org1",
            sql_fingerprint="hash1",
            query_time=1.0
        )

        # Create query in org 2
        query2 = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT secret_data_org2",
            sql_fingerprint="hash2",
            query_time=2.0
        )

        db_session.add_all([query1, query2])
        db_session.commit()

        # User from org 1 queries
        context1 = TenantContext.from_user(sample_user)
        tenant_query1 = get_tenant_aware_query(context1)
        results1 = tenant_query1.filter_slow_queries(db_session.query(SlowQuery)).all()

        # Should only see org 1 queries
        assert len(results1) == 1
        assert results1[0].sql_text == "SELECT secret_data_org1"

        # User from org 2 queries
        context2 = TenantContext.from_user(second_org_user)
        tenant_query2 = get_tenant_aware_query(context2)
        results2 = tenant_query2.filter_slow_queries(db_session.query(SlowQuery)).all()

        # Should only see org 2 queries
        assert len(results2) == 1
        assert results2[0].sql_text == "SELECT secret_data_org2"

    def test_no_cross_tenant_user_visibility(
        self,
        db_session,
        sample_org_admin,
        second_org_user
    ):
        """Test that org admins cannot see users from other organizations."""
        context = TenantContext.from_user(sample_org_admin)
        tenant_query = get_tenant_aware_query(context)

        filtered_users = tenant_query.filter_users(db_session.query(User)).all()

        # Should not include users from other orgs
        user_ids = [u.id for u in filtered_users]
        assert second_org_user.id not in user_ids

    def test_org_admin_cannot_access_other_org_resources(
        self,
        db_session,
        sample_org_admin,
        second_organization,
        second_team
    ):
        """Test that org admin cannot access resources from other organizations."""
        context = TenantContext.from_user(sample_org_admin)

        # Cannot access other organization
        assert context.can_access_organization(second_organization.id) is False

        # Cannot access team in other organization
        assert context.can_access_team(second_team.id, db_session) is False
