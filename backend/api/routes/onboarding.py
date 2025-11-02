"""
Onboarding API routes.

Handles the complete onboarding wizard flow for new customers.
Creates organization, team, collector, and database connections.
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.security import encrypt_db_password
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_active_user
from backend.db.models import (
    User,
    Organization,
    Team,
    TeamMember,
    Collector,
    DatabaseConnection,
    CollectorDatabase
)
from backend.api.schemas.onboarding import (
    OnboardingStartRequest,
    OnboardingStartResponse,
    OnboardingDatabasesRequest,
    OnboardingDatabasesResponse,
    OnboardingStatusResponse,
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    DatabaseConnectionStatus
)

logger = get_logger(__name__)
router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# ONBOARDING START
# =============================================================================


@router.post(
    "/start",
    response_model=OnboardingStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start onboarding process",
    description="Create organization, team, and collector. Generate agent token."
)
async def start_onboarding(
    request: OnboardingStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start the onboarding process.

    Creates:
    - New organization
    - New team within the organization
    - New collector for the team
    - Generates agent token for collector authentication
    - Returns Docker command for customer to run
    """
    try:
        # Generate organization slug if not provided
        org_slug = request.organization_slug
        if not org_slug:
            # Generate from organization name
            org_slug = request.organization_name.lower().replace(' ', '-').replace('_', '-')
            # Remove special characters
            org_slug = ''.join(c for c in org_slug if c.isalnum() or c == '-')

        # Ensure unique slug
        base_slug = org_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        # Create organization
        organization = Organization(
            name=request.organization_name,
            slug=org_slug,
            description=f"Organization created via onboarding by {current_user.full_name}",
            plan_type='FREE',
            is_active=True
        )
        db.add(organization)
        db.flush()

        logger.info(f"Created organization: {organization.name} (ID: {organization.id})")

        # Create team
        team = Team(
            organization_id=organization.id,
            name=request.team_name,
            description="Main team for query analysis",
            is_active=True
        )
        db.add(team)
        db.flush()

        logger.info(f"Created team: {team.name} (ID: {team.id})")

        # Add current user as team OWNER
        team_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role='OWNER'
        )
        db.add(team_member)

        # Create collector
        collector = Collector(
            team_id=team.id,
            organization_id=organization.id,
            name=request.collector_name,
            hostname=request.collector_hostname,
            version=None,  # Will be set by agent on first heartbeat
            status='INACTIVE',  # Will become ACTIVE when agent starts
            last_heartbeat=None
        )
        db.add(collector)
        db.flush()

        logger.info(f"Created collector: {collector.name} (ID: {collector.id})")

        # Generate agent token
        # For onboarding, we'll create a temporary database connection to generate the token
        # The actual databases will be added in the next step
        temp_db_connection = DatabaseConnection(
            team_id=team.id,
            organization_id=organization.id,
            name=f"_onboarding_temp_{collector.id}",
            db_type='mysql',
            host='localhost',
            port=3306,
            database_name='temp',
            username='temp',
            encrypted_password=encrypt_db_password('temp'),
            visibility_scope='TEAM_ONLY',
            owner_user_id=current_user.id,
            is_legacy=False,
            is_active=False  # Inactive until real databases are added
        )

        # Generate agent token
        agent_token = temp_db_connection.generate_agent_token()

        db.add(temp_db_connection)
        db.commit()
        db.refresh(organization)
        db.refresh(team)
        db.refresh(collector)

        # Build Docker command
        docker_command = (
            f"docker run -d --name dbpower-agent "
            f"-e DBPOWER_API_URL=http://localhost:8000/api/v1 "
            f"-e DBPOWER_AGENT_TOKEN={agent_token} "
            f"-e COLLECTOR_ID={collector.id} "
            f"-e ORGANIZATION_ID={organization.id} "
            f"humanaise/dbpower-agent:latest"
        )

        logger.info(f"Onboarding started for user {current_user.email}: org={organization.id}, team={team.id}, collector={collector.id}")

        return OnboardingStartResponse(
            success=True,
            organization_id=organization.id,
            team_id=team.id,
            collector_id=collector.id,
            agent_token=agent_token,
            docker_command=docker_command
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error starting onboarding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start onboarding: {str(e)}"
        )


# =============================================================================
# ADD DATABASES
# =============================================================================


@router.post(
    "/databases",
    response_model=OnboardingDatabasesResponse,
    summary="Add databases to collector",
    description="Add database connections to the collector during onboarding"
)
async def add_databases(
    request: OnboardingDatabasesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add database connections to a collector during onboarding.

    - Validates that collector exists and belongs to user
    - Creates database connections with encrypted passwords
    - Associates databases with collector via collector_databases table
    - Generates unique agent tokens for each database
    """
    try:
        # Get collector and verify ownership
        collector = db.query(Collector).filter(Collector.id == request.collector_id).first()
        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collector with ID {request.collector_id} not found"
            )

        # Verify user has access to this collector (via team membership)
        team_member = db.query(TeamMember).filter(
            TeamMember.team_id == collector.team_id,
            TeamMember.user_id == current_user.id
        ).first()

        if not team_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this collector"
            )

        database_ids = []
        errors = []
        databases_added = 0
        databases_failed = 0

        for db_config in request.databases:
            try:
                # Check if database name already exists for this team
                existing = db.query(DatabaseConnection).filter(
                    DatabaseConnection.team_id == collector.team_id,
                    DatabaseConnection.name == db_config.name
                ).first()

                if existing:
                    errors.append(f"Database '{db_config.name}' already exists in this team")
                    databases_failed += 1
                    continue

                # Encrypt password
                encrypted_password = encrypt_db_password(db_config.password)

                # Create database connection
                db_connection = DatabaseConnection(
                    team_id=collector.team_id,
                    organization_id=collector.organization_id,
                    name=db_config.name,
                    db_type=db_config.db_type,
                    host=db_config.host,
                    port=db_config.port,
                    database_name=db_config.database_name,
                    username=db_config.username,
                    encrypted_password=encrypted_password,
                    ssl_enabled=db_config.ssl_enabled,
                    ssl_ca=db_config.ssl_ca,
                    visibility_scope='TEAM_ONLY',
                    owner_user_id=current_user.id,
                    is_legacy=False,
                    is_active=True
                )

                # Generate agent token
                db_connection.generate_agent_token()

                db.add(db_connection)
                db.flush()

                # Associate database with collector
                collector_db = CollectorDatabase(
                    collector_id=collector.id,
                    database_connection_id=db_connection.id
                )
                db.add(collector_db)

                database_ids.append(db_connection.id)
                databases_added += 1

                logger.info(f"Added database '{db_connection.name}' to collector {collector.id}")

            except Exception as e:
                logger.error(f"Failed to add database '{db_config.name}': {e}")
                errors.append(f"Failed to add '{db_config.name}': {str(e)}")
                databases_failed += 1

        db.commit()

        return OnboardingDatabasesResponse(
            success=databases_added > 0,
            databases_added=databases_added,
            databases_failed=databases_failed,
            database_ids=database_ids,
            errors=errors
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding databases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add databases: {str(e)}"
        )


# =============================================================================
# ONBOARDING STATUS
# =============================================================================


@router.get(
    "/status/{collector_id}",
    response_model=OnboardingStatusResponse,
    summary="Get onboarding status",
    description="Get current status of collector and associated databases"
)
async def get_onboarding_status(
    collector_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get onboarding status for a collector.

    Returns:
    - Collector status (ACTIVE, INACTIVE, ERROR)
    - Last heartbeat timestamp
    - List of databases with their connection status
    - Counts of connected/pending/error databases
    """
    try:
        # Get collector
        collector = db.query(Collector).filter(Collector.id == collector_id).first()
        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collector with ID {collector_id} not found"
            )

        # Verify user has access
        team_member = db.query(TeamMember).filter(
            TeamMember.team_id == collector.team_id,
            TeamMember.user_id == current_user.id
        ).first()

        if not team_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this collector"
            )

        # Get associated databases
        collector_dbs = db.query(CollectorDatabase).filter(
            CollectorDatabase.collector_id == collector_id
        ).all()

        database_statuses = []
        connected = 0
        pending = 0
        error = 0

        for coll_db in collector_dbs:
            db_conn = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == coll_db.database_connection_id
            ).first()

            if db_conn:
                # Determine status based on last_connected_at
                if db_conn.last_connected_at:
                    db_status = "CONNECTED"
                    connected += 1
                else:
                    db_status = "PENDING"
                    pending += 1

                database_statuses.append(DatabaseConnectionStatus(
                    id=db_conn.id,
                    name=db_conn.name,
                    db_type=db_conn.db_type,
                    host=db_conn.host,
                    port=db_conn.port,
                    database_name=db_conn.database_name,
                    status=db_status,
                    last_connected_at=db_conn.last_connected_at,
                    error_message=None
                ))

        return OnboardingStatusResponse(
            collector_id=collector.id,
            collector_name=collector.name,
            collector_status=collector.status,
            last_heartbeat=collector.last_heartbeat,
            databases=database_statuses,
            total_databases=len(database_statuses),
            connected_databases=connected,
            pending_databases=pending,
            error_databases=error
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding status: {str(e)}"
        )


# =============================================================================
# COMPLETE ONBOARDING
# =============================================================================


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    summary="Complete onboarding",
    description="Mark onboarding as complete and verify setup"
)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete the onboarding process.

    - Verifies collector is active
    - Counts configured databases
    - Returns next steps for the user
    """
    try:
        # Get collector
        collector = db.query(Collector).filter(Collector.id == request.collector_id).first()
        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collector with ID {request.collector_id} not found"
            )

        # Verify user has access
        team_member = db.query(TeamMember).filter(
            TeamMember.team_id == collector.team_id,
            TeamMember.user_id == current_user.id
        ).first()

        if not team_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this collector"
            )

        # Count configured databases
        db_count = db.query(CollectorDatabase).filter(
            CollectorDatabase.collector_id == collector.id
        ).count()

        # Build next steps
        next_steps = [
            "View your dashboard to see collected queries",
            "Wait for slow queries to be collected from your databases",
            "Review AI-powered optimization suggestions",
            "Configure alerts for critical slow queries (coming soon)"
        ]

        if collector.status == 'ACTIVE':
            message = f"Onboarding completed successfully! Your collector is actively monitoring {db_count} database(s)."
        else:
            message = f"Onboarding configuration complete! {db_count} database(s) configured. Waiting for collector to come online..."

        logger.info(f"Onboarding completed for collector {collector.id} (user: {current_user.email})")

        return OnboardingCompleteResponse(
            success=True,
            message=message,
            collector_id=collector.id,
            collector_status=collector.status,
            databases_configured=db_count,
            next_steps=next_steps
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing onboarding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )
