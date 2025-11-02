"""
Collector management endpoints for multi-database monitoring.

API routes for:
- Collector registration (agent_token authentication)
- Collector heartbeat
- Collector management (list, get, deactivate)
- Slow query ingestion
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.db.models import (
    User, Team, DatabaseConnection, Collector, CollectorDatabase,
    SlowQueryRaw, Organization
)
from backend.api.schemas.collectors import (
    CollectorRegisterRequest, CollectorRegisterResponse,
    CollectorHeartbeatRequest, CollectorResponse, CollectorListResponse,
    IngestSlowQueriesRequest, IngestSlowQueriesResponse,
    SlowQueryIngestionRequest
)
from backend.core.dependencies import get_current_active_user, get_current_team, require_role
from backend.core.security import create_access_token
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/collectors",
    tags=["Collectors"],
)


# =============================================================================
# COLLECTOR REGISTRATION (NO JWT REQUIRED - USES AGENT_TOKEN)
# =============================================================================


@router.post("/register", response_model=CollectorRegisterResponse)
async def register_collector(
    request: CollectorRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a collector with an agent token.

    Does NOT require JWT authentication - uses agent_token from request.
    Returns a session token (JWT) for subsequent requests.

    The collector will be linked to the database connection associated with the agent_token.
    """
    # Find database connection by agent_token
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.agent_token == request.agent_token,
        DatabaseConnection.is_active == True
    ).first()

    if not db_connection:
        logger.warning(f"Registration failed: Invalid or inactive agent token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent token"
        )

    # Find existing collector by hostname and team
    collector = None
    if request.hostname:
        collector = db.query(Collector).filter(
            Collector.hostname == request.hostname,
            Collector.team_id == db_connection.team_id
        ).first()

    if collector:
        # Update existing collector
        logger.info(f"Updating existing collector {collector.id} for hostname {request.hostname}")
        collector.version = request.version
        collector.config_hash = request.config_hash
        collector.last_heartbeat = datetime.utcnow()
        collector.status = 'ACTIVE'
    else:
        # Create new collector
        collector = Collector(
            team_id=db_connection.team_id,
            organization_id=db_connection.organization_id,
            name=request.hostname or "Unnamed Collector",
            hostname=request.hostname,
            version=request.version,
            config_hash=request.config_hash,
            last_heartbeat=datetime.utcnow(),
            status='ACTIVE'
        )
        db.add(collector)
        db.flush()  # Get collector.id
        logger.info(f"Created new collector {collector.id} for hostname {request.hostname}")

    # Link collector to database connection (if not already linked)
    existing_link = db.query(CollectorDatabase).filter(
        CollectorDatabase.collector_id == collector.id,
        CollectorDatabase.database_connection_id == db_connection.id
    ).first()

    if not existing_link:
        collector_db_link = CollectorDatabase(
            collector_id=collector.id,
            database_connection_id=db_connection.id
        )
        db.add(collector_db_link)
        logger.info(f"Linked collector {collector.id} to database connection {db_connection.id}")

    db.commit()
    db.refresh(collector)

    # Generate session token (JWT) for the collector
    token_data = {
        "sub": str(collector.id),
        "database_connection_id": str(db_connection.id),
        "team_id": str(db_connection.team_id),
        "organization_id": str(db_connection.organization_id),
        "type": "collector"
    }
    expires_delta = timedelta(days=365)  # Long-lived token for collectors
    session_token = create_access_token(data=token_data, expires_delta=expires_delta)
    expires_at = datetime.utcnow() + expires_delta

    logger.info(
        f"Collector {collector.id} registered successfully. "
        f"Token expires: {expires_at.isoformat()}"
    )

    return CollectorRegisterResponse(
        collector_id=collector.id,
        database_connection_id=db_connection.id,
        session_token=session_token,
        expires_at=expires_at
    )


# =============================================================================
# SLOW QUERY INGESTION (NO JWT REQUIRED - USES AGENT_TOKEN)
# =============================================================================


@router.post("/ingest/slow-queries", response_model=IngestSlowQueriesResponse)
async def ingest_slow_queries(
    request: IngestSlowQueriesRequest,
    db: Session = Depends(get_db)
):
    """
    Unified ingestion endpoint for slow queries.

    Does NOT require JWT authentication - uses agent_token from request.
    Accepts queries from any database type (MySQL, PostgreSQL, etc.).
    """
    # Authenticate using agent_token
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.agent_token == request.agent_token,
        DatabaseConnection.is_active == True
    ).first()

    if not db_connection:
        logger.warning("Ingestion failed: Invalid or inactive agent token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent token"
        )

    queries_received = len(request.queries)
    queries_stored = 0
    queries_skipped = 0
    errors = []

    logger.info(
        f"Ingestion started: {queries_received} queries for database "
        f"{db_connection.name} (ID: {db_connection.id})"
    )

    for idx, query_data in enumerate(request.queries):
        try:
            # Check for duplicate (same fingerprint and captured_at within 1 minute)
            existing = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.database_connection_id == db_connection.id,
                SlowQueryRaw.fingerprint == query_data.fingerprint,
                SlowQueryRaw.captured_at >= query_data.captured_at - timedelta(minutes=1),
                SlowQueryRaw.captured_at <= query_data.captured_at + timedelta(minutes=1)
            ).first()

            if existing:
                queries_skipped += 1
                logger.debug(f"Skipped duplicate query: {query_data.fingerprint[:50]}...")
                continue

            # Create slow query record
            slow_query = SlowQueryRaw(
                team_id=db_connection.team_id,
                organization_id=db_connection.organization_id,
                database_connection_id=db_connection.id,
                fingerprint=query_data.fingerprint,
                full_sql=query_data.full_sql,
                duration_ms=query_data.duration_ms,
                rows_examined=query_data.rows_examined,
                rows_returned=query_data.rows_returned,
                captured_at=query_data.captured_at,
                plan_json=query_data.plan_json,
                plan_text=query_data.plan_text,
                # Preserve source metadata for compatibility
                source_db_type=db_connection.db_type,
                source_db_host=db_connection.host,
                source_db_name=db_connection.database_name,
            )
            db.add(slow_query)
            queries_stored += 1

        except Exception as e:
            error_msg = f"Query {idx + 1}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Failed to store query {idx + 1}: {e}", exc_info=True)

    # Commit all queries at once
    try:
        db.commit()
        logger.info(
            f"Ingestion completed: {queries_stored} stored, {queries_skipped} skipped, "
            f"{len(errors)} errors"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit ingestion batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store queries: {str(e)}"
        )

    return IngestSlowQueriesResponse(
        success=len(errors) == 0,
        queries_received=queries_received,
        queries_stored=queries_stored,
        queries_skipped=queries_skipped,
        errors=errors
    )


# =============================================================================
# COLLECTOR CONFIG (NO JWT REQUIRED - USES AGENT_TOKEN)
# =============================================================================


@router.get("/config")
async def get_collector_config(
    agent_token: str,
    db: Session = Depends(get_db)
):
    """
    Get collector configuration including database connections to monitor.

    Does NOT require JWT authentication - uses agent_token from query parameter.
    This endpoint is called by the collector agent to get its configuration.

    Returns list of databases this collector should monitor.
    """
    # Find collector by agent_token through database connections
    db_connections = db.query(DatabaseConnection).filter(
        DatabaseConnection.agent_token == agent_token,
        DatabaseConnection.is_active == True
    ).all()

    if not db_connections:
        logger.warning("Config fetch failed: Invalid or inactive agent token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent token"
        )

    # Get the team and organization from the first database connection
    first_conn = db_connections[0]
    team_id = first_conn.team_id
    organization_id = first_conn.organization_id

    # Get all collectors for this team that might be associated with these databases
    collectors = db.query(Collector).filter(
        Collector.team_id == team_id
    ).all()

    # Get all database connections for this collector via collector_databases
    all_db_connections = []
    for collector in collectors:
        collector_dbs = db.query(CollectorDatabase).filter(
            CollectorDatabase.collector_id == collector.id
        ).all()

        for coll_db in collector_dbs:
            db_conn = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == coll_db.database_connection_id,
                DatabaseConnection.is_active == True
            ).first()

            if db_conn and db_conn not in all_db_connections:
                all_db_connections.append(db_conn)

    # If no databases found via collector_databases, use the ones with matching agent_token
    if not all_db_connections:
        all_db_connections = db_connections

    # Build database config list
    databases = []
    for db_conn in all_db_connections:
        from backend.core.security import decrypt_db_password
        try:
            decrypted_password = decrypt_db_password(db_conn.encrypted_password)
        except Exception as e:
            logger.error(f"Failed to decrypt password for database {db_conn.id}: {e}")
            continue

        databases.append({
            "id": str(db_conn.id),
            "name": db_conn.name,
            "db_type": db_conn.db_type,
            "host": db_conn.host,
            "port": db_conn.port,
            "database_name": db_conn.database_name,
            "username": db_conn.username,
            "password": decrypted_password,
            "ssl_enabled": db_conn.ssl_enabled,
            "ssl_ca": db_conn.ssl_ca
        })

    logger.info(f"Config fetched for team {team_id}: {len(databases)} databases")

    return {
        "success": True,
        "organization_id": str(organization_id),
        "team_id": str(team_id),
        "databases": databases,
        "collection_interval_seconds": 300  # 5 minutes default
    }


# =============================================================================
# COLLECTOR HEARTBEAT (NO JWT REQUIRED - USES AGENT_TOKEN)
# =============================================================================


@router.post("/heartbeat")
async def collector_heartbeat(
    request: CollectorHeartbeatRequest,
    agent_token: str,
    db: Session = Depends(get_db)
):
    """
    Update collector heartbeat and status.

    Does NOT require JWT authentication - uses agent_token from query parameter.
    This endpoint is called periodically by the collector agent.
    """
    # Find database connection by agent_token
    db_connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.agent_token == agent_token,
        DatabaseConnection.is_active == True
    ).first()

    if not db_connection:
        logger.warning("Heartbeat failed: Invalid or inactive agent token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent token"
        )

    # Find or create collector for this database connection
    # Try to find existing collector linked to this database
    collector_db_link = db.query(CollectorDatabase).filter(
        CollectorDatabase.database_connection_id == db_connection.id
    ).first()

    if collector_db_link:
        collector = db.query(Collector).filter(
            Collector.id == collector_db_link.collector_id
        ).first()
    else:
        # No collector found, create one
        collector = Collector(
            team_id=db_connection.team_id,
            organization_id=db_connection.organization_id,
            name=f"Auto-created collector for {db_connection.name}",
            hostname=None,
            version=None,
            status='ACTIVE',
            last_heartbeat=datetime.utcnow()
        )
        db.add(collector)
        db.flush()

        # Link collector to database
        new_link = CollectorDatabase(
            collector_id=collector.id,
            database_connection_id=db_connection.id
        )
        db.add(new_link)

    # Update heartbeat and status
    collector.last_heartbeat = datetime.utcnow()
    if request.status:
        collector.status = request.status

    # Update database connection's last_connected_at
    db_connection.last_connected_at = datetime.utcnow()

    db.commit()
    db.refresh(collector)

    logger.info(f"Heartbeat received from collector {collector.id}, status: {collector.status}")

    return {
        "success": True,
        "collector_id": str(collector.id),
        "last_heartbeat": collector.last_heartbeat.isoformat(),
        "status": collector.status
    }


# =============================================================================
# LEGACY COLLECTOR HEARTBEAT (REQUIRES JWT SESSION TOKEN)
# =============================================================================


@router.post("/{collector_id}/heartbeat")
async def collector_heartbeat_legacy(
    collector_id: UUID,
    request: CollectorHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team)
):
    """
    Update collector heartbeat and status (legacy endpoint with JWT).

    Requires JWT authentication (session token from registration).
    Kept for backward compatibility.
    """
    # Get collector
    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.team_id == current_team.id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector not found"
        )

    # Update heartbeat and status
    collector.last_heartbeat = datetime.utcnow()
    if request.status:
        collector.status = request.status

    db.commit()

    logger.info(f"Heartbeat received from collector {collector_id}, status: {collector.status}")

    return {
        "success": True,
        "collector_id": str(collector_id),
        "last_heartbeat": collector.last_heartbeat.isoformat(),
        "status": collector.status
    }


# =============================================================================
# COLLECTOR MANAGEMENT (REQUIRES JWT AUTHENTICATION + ROLE)
# =============================================================================


@router.get("", response_model=CollectorListResponse)
async def list_collectors(
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    List all collectors for the current team.

    Returns collectors with their associated database connections.
    """
    collectors = db.query(Collector).filter(
        Collector.team_id == current_team.id
    ).order_by(Collector.created_at.desc()).all()

    logger.debug(f"Found {len(collectors)} collectors for team {current_team.id}")

    return CollectorListResponse(
        total=len(collectors),
        collectors=collectors
    )


@router.get("/status")
async def get_collectors_status(
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get collector and scheduler status for the current team.

    Returns information about scheduled collection jobs and statistics.
    """
    # Check if scheduler is running (always True in this implementation as it starts with app)
    is_running = True

    # Get collection statistics for this team
    mysql_count = db.query(func.count(SlowQueryRaw.id)).filter(
        SlowQueryRaw.team_id == current_team.id,
        SlowQueryRaw.source_db_type == 'mysql'
    ).scalar() or 0

    postgres_count = db.query(func.count(SlowQueryRaw.id)).filter(
        SlowQueryRaw.team_id == current_team.id,
        SlowQueryRaw.source_db_type == 'postgres'
    ).scalar() or 0

    # Get last collection times
    mysql_last = db.query(func.max(SlowQueryRaw.captured_at)).filter(
        SlowQueryRaw.team_id == current_team.id,
        SlowQueryRaw.source_db_type == 'mysql'
    ).scalar()

    postgres_last = db.query(func.max(SlowQueryRaw.captured_at)).filter(
        SlowQueryRaw.team_id == current_team.id,
        SlowQueryRaw.source_db_type == 'postgres'
    ).scalar()

    # Count analyzed queries
    from backend.db.models import AnalysisResult
    analyzed_count = db.query(func.count(AnalysisResult.id)).join(
        SlowQueryRaw, AnalysisResult.slow_query_id == SlowQueryRaw.id
    ).filter(
        SlowQueryRaw.team_id == current_team.id
    ).scalar() or 0

    # Return scheduler-style response for compatibility
    return {
        "is_running": is_running,
        "jobs": [
            {
                "id": "mysql_collector",
                "name": "MySQL Slow Query Collector",
                "next_run": None  # APScheduler runs in background, no next_run exposed
            },
            {
                "id": "postgres_collector",
                "name": "PostgreSQL Slow Query Collector",
                "next_run": None
            }
        ],
        "mysql_last_run": mysql_last.isoformat() if mysql_last else None,
        "postgres_last_run": postgres_last.isoformat() if postgres_last else None,
        "analyzer_last_run": None,
        "mysql_total_collected": mysql_count,
        "postgres_total_collected": postgres_count,
        "total_analyzed": analyzed_count
    }


@router.get("/{collector_id}", response_model=CollectorResponse)
async def get_collector(
    collector_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get details for a specific collector.
    """
    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.team_id == current_team.id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector not found"
        )

    return collector


@router.post("/{collector_id}/deactivate", dependencies=[Depends(require_role(["OWNER", "ADMIN"]))])
async def deactivate_collector(
    collector_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Deactivate a collector (mark as INACTIVE).

    Requires OWNER or ADMIN role.
    """
    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.team_id == current_team.id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector not found"
        )

    collector.status = 'INACTIVE'
    db.commit()

    logger.info(f"Collector {collector_id} deactivated by user {current_user.email}")

    return {
        "success": True,
        "message": "Collector deactivated successfully",
        "collector_id": str(collector_id),
        "status": "INACTIVE"
    }
