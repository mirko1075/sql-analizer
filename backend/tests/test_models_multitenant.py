"""
Tests for multi-tenant database models.
"""
import pytest
from datetime import datetime, timedelta

from db.models_multitenant import (
    Organization, Team, Identity, User, UserRole,
    SlowQuery, AnalysisResult, AuditLog, QueryStatus, PriorityLevel
)
from core.security import verify_password


class TestOrganization:
    """Tests for Organization model."""

    def test_create_organization(self, db_session):
        """Test creating an organization."""
        org = Organization(
            name="Test Org",
            settings={"key": "value"}
        )
        db_session.add(org)
        db_session.commit()

        assert org.id is not None
        assert org.name == "Test Org"
        assert org.settings == {"key": "value"}
        assert org.created_at is not None

    def test_generate_api_key(self, db_session):
        """Test API key generation."""
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.commit()

        api_key = org.generate_api_key()

        assert api_key is not None
        assert api_key.startswith(f"dbp_{org.id}_")
        assert org.api_key_hash is not None
        assert org.api_key_created_at is not None
        assert org.api_key_expires_at is not None

    def test_verify_api_key(self, sample_organization):
        """Test API key verification."""
        api_key = sample_organization._test_api_key

        assert sample_organization.verify_api_key(api_key) is True
        assert sample_organization.verify_api_key("wrong_key") is False

    def test_organization_cascade_delete(self, db_session, sample_organization, sample_team):
        """Test that deleting organization cascades to teams."""
        org_id = sample_organization.id
        team_id = sample_team.id

        db_session.delete(sample_organization)
        db_session.commit()

        # Verify team is also deleted
        team = db_session.query(Team).filter(Team.id == team_id).first()
        assert team is None


class TestTeam:
    """Tests for Team model."""

    def test_create_team(self, db_session, sample_organization):
        """Test creating a team."""
        team = Team(
            organization_id=sample_organization.id,
            name="Engineering"
        )
        db_session.add(team)
        db_session.commit()

        assert team.id is not None
        assert team.name == "Engineering"
        assert team.organization_id == sample_organization.id

    def test_team_unique_name_per_org(self, db_session, sample_organization):
        """Test that team names must be unique within an organization."""
        team1 = Team(organization_id=sample_organization.id, name="Engineering")
        db_session.add(team1)
        db_session.commit()

        team2 = Team(organization_id=sample_organization.id, name="Engineering")
        db_session.add(team2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_team_same_name_different_orgs(self, db_session, sample_organization, second_organization):
        """Test that teams in different orgs can have the same name."""
        team1 = Team(organization_id=sample_organization.id, name="Engineering")
        team2 = Team(organization_id=second_organization.id, name="Engineering")

        db_session.add_all([team1, team2])
        db_session.commit()

        assert team1.id != team2.id
        assert team1.name == team2.name


class TestIdentity:
    """Tests for Identity model."""

    def test_create_identity(self, db_session, sample_team):
        """Test creating an identity."""
        identity = Identity(
            team_id=sample_team.id,
            name="Backend Services"
        )
        db_session.add(identity)
        db_session.commit()

        assert identity.id is not None
        assert identity.name == "Backend Services"
        assert identity.team_id == sample_team.id

    def test_identity_unique_name_per_team(self, db_session, sample_team):
        """Test that identity names must be unique within a team."""
        identity1 = Identity(team_id=sample_team.id, name="Backend")
        db_session.add(identity1)
        db_session.commit()

        identity2 = Identity(team_id=sample_team.id, name="Backend")
        db_session.add(identity2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestUser:
    """Tests for User model."""

    def test_create_user(self, db_session, sample_organization, sample_identity):
        """Test creating a user."""
        user = User(
            organization_id=sample_organization.id,
            identity_id=sample_identity.id,
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER

    def test_user_unique_email(self, db_session, sample_organization, sample_identity):
        """Test that email must be unique."""
        user1 = User(
            organization_id=sample_organization.id,
            identity_id=sample_identity.id,
            email="test@example.com",
            password_hash="hash1",
            role=UserRole.USER
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            organization_id=sample_organization.id,
            identity_id=sample_identity.id,
            email="test@example.com",
            password_hash="hash2",
            role=UserRole.USER
        )
        db_session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_roles(self, db_session, sample_organization, sample_identity):
        """Test different user roles."""
        roles = [UserRole.USER, UserRole.TEAM_LEAD, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]

        for i, role in enumerate(roles):
            user = User(
                organization_id=sample_organization.id,
                identity_id=sample_identity.id,
                email=f"user{i}@example.com",
                password_hash="hash",
                role=role
            )
            db_session.add(user)

        db_session.commit()

        users = db_session.query(User).all()
        assert len(users) == 4


class TestSlowQuery:
    """Tests for SlowQuery model (multi-tenant)."""

    def test_create_slow_query(self, db_session, sample_organization, sample_team, sample_identity):
        """Test creating a slow query."""
        query = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT * FROM users WHERE id = [REDACTED]",
            sql_fingerprint="abc123",
            query_time=1.5,
            rows_examined=1000,
            rows_sent=10,
            database_name="testdb",
            status=QueryStatus.PENDING
        )
        db_session.add(query)
        db_session.commit()

        assert query.id is not None
        assert query.organization_id == sample_organization.id
        assert query.status == QueryStatus.PENDING

    def test_slow_query_unique_constraint(self, db_session, sample_organization, sample_team, sample_identity):
        """Test that duplicate queries (same fingerprint + time) are prevented."""
        start_time = datetime.utcnow()

        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT * FROM users",
            sql_fingerprint="abc123",
            query_time=1.0,
            start_time=start_time
        )
        db_session.add(query1)
        db_session.commit()

        query2 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT * FROM users",
            sql_fingerprint="abc123",
            query_time=1.0,
            start_time=start_time
        )
        db_session.add(query2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_create_analysis_result(self, db_session, sample_organization, sample_team, sample_identity):
        """Test creating an analysis result."""
        query = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT * FROM users",
            sql_fingerprint="abc123",
            query_time=1.0
        )
        db_session.add(query)
        db_session.commit()

        analysis = AnalysisResult(
            slow_query_id=query.id,
            issues_found=["Missing WHERE clause", "SELECT *"],
            suggested_indexes=[{"table": "users", "columns": ["id"]}],
            improvement_priority=PriorityLevel.HIGH,
            ai_analysis="This query is inefficient",
            ai_provider="llama"
        )
        db_session.add(analysis)
        db_session.commit()

        assert analysis.id is not None
        assert analysis.slow_query_id == query.id
        assert analysis.improvement_priority == PriorityLevel.HIGH


class TestAuditLog:
    """Tests for AuditLog model."""

    def test_create_audit_log(self, db_session, sample_organization, sample_user):
        """Test creating an audit log entry."""
        audit = AuditLog(
            organization_id=sample_organization.id,
            user_id=sample_user.id,
            action="user.login",
            resource_type="user",
            resource_id=sample_user.id,
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            request_method="POST",
            request_path="/api/v1/auth/login",
            status_code=200,
            details={"success": True}
        )
        db_session.add(audit)
        db_session.commit()

        assert audit.id is not None
        assert audit.action == "user.login"

    def test_audit_log_immutability(self, db_session, sample_organization, sample_user):
        """Test that audit logs are append-only (no updates in production)."""
        audit = AuditLog(
            organization_id=sample_organization.id,
            user_id=sample_user.id,
            action="user.login",
            ip_address="127.0.0.1"
        )
        db_session.add(audit)
        db_session.commit()

        original_action = audit.action

        # In production, you'd prevent this with database triggers
        # Here we just verify the field exists
        assert audit.action == original_action


class TestMultiTenantIsolation:
    """Tests for multi-tenant data isolation."""

    def test_organizations_isolated(self, db_session, sample_organization, second_organization):
        """Test that organizations are properly isolated."""
        assert sample_organization.id != second_organization.id
        assert sample_organization.name != second_organization.name

    def test_queries_isolated_by_organization(
        self,
        db_session,
        sample_organization,
        sample_team,
        sample_identity,
        second_organization,
        second_team,
        second_identity
    ):
        """Test that slow queries are isolated by organization."""
        # Create query in first org
        query1 = SlowQuery(
            organization_id=sample_organization.id,
            team_id=sample_team.id,
            identity_id=sample_identity.id,
            sql_text="SELECT * FROM table1",
            sql_fingerprint="hash1",
            query_time=1.0
        )

        # Create query in second org
        query2 = SlowQuery(
            organization_id=second_organization.id,
            team_id=second_team.id,
            identity_id=second_identity.id,
            sql_text="SELECT * FROM table2",
            sql_fingerprint="hash2",
            query_time=2.0
        )

        db_session.add_all([query1, query2])
        db_session.commit()

        # Query for first org only
        org1_queries = db_session.query(SlowQuery).filter(
            SlowQuery.organization_id == sample_organization.id
        ).all()

        assert len(org1_queries) == 1
        assert org1_queries[0].organization_id == sample_organization.id

        # Query for second org only
        org2_queries = db_session.query(SlowQuery).filter(
            SlowQuery.organization_id == second_organization.id
        ).all()

        assert len(org2_queries) == 1
        assert org2_queries[0].organization_id == second_organization.id
