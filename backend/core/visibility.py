"""
Visibility filtering logic for multi-database monitoring.

Handles database connection visibility based on scope:
- TEAM_ONLY: Only team members can see
- ORG_WIDE: All organization members can see
- USER_ONLY: Only the owner can see
"""
from typing import List, Set
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.db.models import User, Team, TeamMember, DatabaseConnection, Organization
from backend.core.logger import get_logger

logger = get_logger(__name__)


def get_user_team_ids(user: User, db: Session) -> Set[UUID]:
    """
    Get all team IDs the user belongs to.

    Args:
        user: User object
        db: Database session

    Returns:
        Set of team UUIDs
    """
    team_memberships = db.query(TeamMember.team_id).filter(
        TeamMember.user_id == user.id
    ).all()

    return {team_id for (team_id,) in team_memberships}


def get_user_organization_ids(user: User, db: Session) -> Set[UUID]:
    """
    Get all organization IDs the user belongs to (via team memberships).

    Args:
        user: User object
        db: Database session

    Returns:
        Set of organization UUIDs
    """
    org_ids = db.query(Team.organization_id).join(
        TeamMember, Team.id == TeamMember.team_id
    ).filter(
        TeamMember.user_id == user.id
    ).distinct().all()

    return {org_id for (org_id,) in org_ids}


def get_visible_database_connections(
    user: User,
    db: Session,
    team_id: UUID = None,
    include_inactive: bool = False
) -> List[DatabaseConnection]:
    """
    Get all database connections visible to the user based on visibility scope.

    Visibility rules:
    - TEAM_ONLY: User must be a member of the team
    - ORG_WIDE: User must be a member of any team in the organization
    - USER_ONLY: User must be the owner

    Args:
        user: User object
        db: Database session
        team_id: Optional team filter (only show connections for this team)
        include_inactive: Include inactive connections (default: False)

    Returns:
        List of DatabaseConnection objects
    """
    # Get user's teams and organizations
    user_team_ids = get_user_team_ids(user, db)
    user_org_ids = get_user_organization_ids(user, db)

    if not user_team_ids:
        logger.warning(f"User {user.email} has no team memberships")
        return []

    # Build visibility filter
    visibility_filters = []

    # TEAM_ONLY: User must be in the team
    team_only_filter = and_(
        DatabaseConnection.visibility_scope == 'TEAM_ONLY',
        DatabaseConnection.team_id.in_(user_team_ids)
    )
    visibility_filters.append(team_only_filter)

    # ORG_WIDE: User must be in the organization
    if user_org_ids:
        org_wide_filter = and_(
            DatabaseConnection.visibility_scope == 'ORG_WIDE',
            DatabaseConnection.organization_id.in_(user_org_ids)
        )
        visibility_filters.append(org_wide_filter)

    # USER_ONLY: User must be the owner
    user_only_filter = and_(
        DatabaseConnection.visibility_scope == 'USER_ONLY',
        DatabaseConnection.owner_user_id == user.id
    )
    visibility_filters.append(user_only_filter)

    # Build query
    query = db.query(DatabaseConnection).filter(
        or_(*visibility_filters)
    )

    # Apply team filter if specified
    if team_id:
        query = query.filter(DatabaseConnection.team_id == team_id)

    # Filter active connections only
    if not include_inactive:
        query = query.filter(DatabaseConnection.is_active == True)

    connections = query.all()

    logger.debug(
        f"User {user.email} can see {len(connections)} database connection(s) "
        f"(teams: {len(user_team_ids)}, orgs: {len(user_org_ids)})"
    )

    return connections


def get_visible_database_connection_ids(
    user: User,
    db: Session,
    team_id: UUID = None,
    include_inactive: bool = False
) -> List[UUID]:
    """
    Get IDs of all database connections visible to the user.

    This is optimized for filtering queries.

    Args:
        user: User object
        db: Database session
        team_id: Optional team filter
        include_inactive: Include inactive connections (default: False)

    Returns:
        List of database connection UUIDs
    """
    # Get user's teams and organizations
    user_team_ids = get_user_team_ids(user, db)
    user_org_ids = get_user_organization_ids(user, db)

    if not user_team_ids:
        logger.warning(f"User {user.email} has no team memberships")
        return []

    # Build visibility filter
    visibility_filters = []

    # TEAM_ONLY: User must be in the team
    team_only_filter = and_(
        DatabaseConnection.visibility_scope == 'TEAM_ONLY',
        DatabaseConnection.team_id.in_(user_team_ids)
    )
    visibility_filters.append(team_only_filter)

    # ORG_WIDE: User must be in the organization
    if user_org_ids:
        org_wide_filter = and_(
            DatabaseConnection.visibility_scope == 'ORG_WIDE',
            DatabaseConnection.organization_id.in_(user_org_ids)
        )
        visibility_filters.append(org_wide_filter)

    # USER_ONLY: User must be the owner
    user_only_filter = and_(
        DatabaseConnection.visibility_scope == 'USER_ONLY',
        DatabaseConnection.owner_user_id == user.id
    )
    visibility_filters.append(user_only_filter)

    # Build query
    query = db.query(DatabaseConnection.id).filter(
        or_(*visibility_filters)
    )

    # Apply team filter if specified
    if team_id:
        query = query.filter(DatabaseConnection.team_id == team_id)

    # Filter active connections only
    if not include_inactive:
        query = query.filter(DatabaseConnection.is_active == True)

    connection_ids = [conn_id for (conn_id,) in query.all()]

    logger.debug(
        f"User {user.email} can see {len(connection_ids)} database connection ID(s)"
    )

    return connection_ids


def can_user_see_database_connection(
    user: User,
    connection: DatabaseConnection,
    db: Session
) -> bool:
    """
    Check if a user can see a specific database connection.

    Args:
        user: User object
        connection: DatabaseConnection object
        db: Database session

    Returns:
        True if user can see the connection, False otherwise
    """
    # Get user's teams and organizations
    user_team_ids = get_user_team_ids(user, db)
    user_org_ids = get_user_organization_ids(user, db)

    # Check visibility based on scope
    if connection.visibility_scope == 'TEAM_ONLY':
        return connection.team_id in user_team_ids

    elif connection.visibility_scope == 'ORG_WIDE':
        return connection.organization_id in user_org_ids

    elif connection.visibility_scope == 'USER_ONLY':
        return connection.owner_user_id == user.id

    # Unknown visibility scope - deny by default
    logger.warning(
        f"Unknown visibility scope '{connection.visibility_scope}' "
        f"for connection {connection.id}"
    )
    return False


def filter_query_by_visible_connections(query, user: User, db: Session):
    """
    Apply visibility filtering to a SQLAlchemy query that involves database_connection_id.

    This is a helper function to filter queries on SlowQueryRaw, QueryMetricsDaily, etc.

    Args:
        query: SQLAlchemy query object
        user: User object
        db: Database session

    Returns:
        Filtered query
    """
    visible_connection_ids = get_visible_database_connection_ids(user, db)

    if not visible_connection_ids:
        # User can't see any connections - return empty result
        # We filter by a condition that's always false
        return query.filter(False)

    # Filter by visible connection IDs
    return query.filter(
        # Assuming the model has database_connection_id column
        # This will work with SlowQueryRaw, QueryMetricsDaily, QueryFingerprintMetrics
        query.column_descriptions[0]['type'].database_connection_id.in_(visible_connection_ids)
    )
