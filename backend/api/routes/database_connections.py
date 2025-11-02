"""
Database Connections API routes.

Handles CRUD operations for database connections with encrypted credentials.
"""
import time
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.db.session import get_db
from backend.core.security import encrypt_db_password, decrypt_db_password
from backend.core.logger import get_logger
from backend.core.dependencies import (
    get_current_active_user,
    get_current_team,
    require_role,
    get_visible_database_connections
)
from backend.db.models import (
    User,
    Team,
    DatabaseConnection,
    TeamMember
)
from backend.api.schemas.database_connections import (
    DatabaseConnectionCreateRequest,
    DatabaseConnectionUpdateRequest,
    DatabaseConnectionTestRequest,
    DatabaseConnectionResponse,
    DatabaseConnectionTestResponse,
    DatabaseConnectionListResponse
)
from backend.api.schemas.auth import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/database-connections", tags=["Database Connections"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def test_database_connection(
    db_type: str,
    host: str,
    port: int,
    database_name: str,
    username: str,
    password: str,
    ssl_enabled: bool = False
) -> DatabaseConnectionTestResponse:
    """
    Test a database connection.

    Args:
        db_type: Database type (mysql, postgres, etc.)
        host: Database host
        port: Database port
        database_name: Database name
        username: Database username
        password: Database password
        ssl_enabled: Enable SSL/TLS

    Returns:
        DatabaseConnectionTestResponse with test results
    """
    start_time = time.time()

    try:
        if db_type == 'mysql':
            import mysql.connector
            conn = mysql.connector.connect(
                host=host,
                port=port,
                database=database_name,
                user=username,
                password=password,
                ssl_disabled=not ssl_enabled,
                connect_timeout=10
            )
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

        elif db_type in ['postgres', 'postgresql']:
            import psycopg2
            conn_string = f"host={host} port={port} dbname={database_name} user={username} password={password}"
            if ssl_enabled:
                conn_string += " sslmode=require"
            conn = psycopg2.connect(conn_string, connect_timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0].split(',')[0]  # Extract version number
            cursor.close()
            conn.close()

        else:
            return DatabaseConnectionTestResponse(
                success=False,
                message=f"Database type '{db_type}' not yet supported for testing",
                server_version=None,
                latency_ms=None
            )

        latency = (time.time() - start_time) * 1000  # Convert to ms

        return DatabaseConnectionTestResponse(
            success=True,
            message="Connection successful",
            server_version=version,
            latency_ms=round(latency, 2)
        )

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return DatabaseConnectionTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            server_version=None,
            latency_ms=None
        )


# =============================================================================
# LIST CONNECTIONS
# =============================================================================


@router.get(
    "",
    response_model=DatabaseConnectionListResponse,
    summary="List database connections",
    description="Get all database connections visible to the current user"
)
async def list_connections(
    connections: List[DatabaseConnection] = Depends(get_visible_database_connections),
):
    """
    List all database connections visible to the current user.

    Uses visibility filtering based on scope:
    - TEAM_ONLY: Team members only
    - ORG_WIDE: All organization members
    - USER_ONLY: Owner only

    Returns connections ordered by name.
    """
    try:
        # Sort by name
        sorted_connections = sorted(connections, key=lambda c: c.name)

        return DatabaseConnectionListResponse(
            total=len(sorted_connections),
            connections=sorted_connections
        )

    except Exception as e:
        logger.error(f"Error listing database connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list database connections"
        )


# =============================================================================
# CREATE CONNECTION
# =============================================================================


@router.post(
    "",
    response_model=DatabaseConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create database connection",
    description="Create a new database connection for the current team (requires OWNER or ADMIN role)",
    dependencies=[Depends(require_role(["OWNER", "ADMIN"]))]
)
async def create_connection(
    request: DatabaseConnectionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Create a new database connection.

    - Encrypts the password before storage
    - Validates that connection name is unique within the team
    - Requires OWNER or ADMIN role
    """
    try:
        # Check if connection name already exists for this team
        existing = db.query(DatabaseConnection).filter(
            DatabaseConnection.team_id == current_team.id,
            DatabaseConnection.name == request.name
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection with name '{request.name}' already exists in this team"
            )

        # Encrypt password
        encrypted_password = encrypt_db_password(request.password)

        # Create connection
        connection = DatabaseConnection(
            team_id=current_team.id,
            organization_id=current_team.organization_id,
            name=request.name,
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            username=request.username,
            encrypted_password=encrypted_password,
            ssl_enabled=request.ssl_enabled,
            ssl_ca=request.ssl_ca,
            visibility_scope=request.visibility_scope or 'TEAM_ONLY',
            owner_user_id=current_user.id,
            is_legacy=False,
            is_active=True
        )

        # Generate agent token
        connection.generate_agent_token()

        db.add(connection)
        db.commit()
        db.refresh(connection)

        logger.info(
            f"User {current_user.email} created database connection '{connection.name}' "
            f"for team {current_team.name}"
        )

        return connection

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create database connection"
        )


# =============================================================================
# GET CONNECTION
# =============================================================================


@router.get(
    "/{connection_id}",
    response_model=DatabaseConnectionResponse,
    summary="Get database connection",
    description="Get details of a specific database connection"
)
async def get_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific database connection.

    Ensures the connection belongs to the current team.
    """
    try:
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        return connection

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database connection"
        )


# =============================================================================
# UPDATE CONNECTION
# =============================================================================


@router.put(
    "/{connection_id}",
    response_model=DatabaseConnectionResponse,
    summary="Update database connection",
    description="Update a database connection (requires OWNER or ADMIN role)",
    dependencies=[Depends(require_role(["OWNER", "ADMIN"]))]
)
async def update_connection(
    connection_id: UUID,
    request: DatabaseConnectionUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Update a database connection.

    - Only updates provided fields
    - Encrypts new password if provided
    - Requires OWNER or ADMIN role
    """
    try:
        # Get connection
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        # Check name uniqueness if updating name
        if request.name and request.name != connection.name:
            existing = db.query(DatabaseConnection).filter(
                DatabaseConnection.team_id == current_team.id,
                DatabaseConnection.name == request.name,
                DatabaseConnection.id != connection_id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Connection with name '{request.name}' already exists in this team"
                )

        # Update fields
        if request.name is not None:
            connection.name = request.name
        if request.host is not None:
            connection.host = request.host
        if request.port is not None:
            connection.port = request.port
        if request.database_name is not None:
            connection.database_name = request.database_name
        if request.username is not None:
            connection.username = request.username
        if request.password is not None:
            connection.encrypted_password = encrypt_db_password(request.password)
        if request.ssl_enabled is not None:
            connection.ssl_enabled = request.ssl_enabled
        if request.ssl_ca is not None:
            connection.ssl_ca = request.ssl_ca
        if request.visibility_scope is not None:
            connection.visibility_scope = request.visibility_scope
        if request.is_active is not None:
            connection.is_active = request.is_active

        db.commit()
        db.refresh(connection)

        logger.info(
            f"User {current_user.email} updated database connection '{connection.name}' "
            f"for team {current_team.name}"
        )

        return connection

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database connection"
        )


# =============================================================================
# DELETE CONNECTION
# =============================================================================


@router.delete(
    "/{connection_id}",
    response_model=MessageResponse,
    summary="Delete database connection",
    description="Delete a database connection (requires OWNER or ADMIN role)",
    dependencies=[Depends(require_role(["OWNER", "ADMIN"]))]
)
async def delete_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Delete a database connection.

    Requires OWNER or ADMIN role.
    """
    try:
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        connection_name = connection.name
        db.delete(connection)
        db.commit()

        logger.info(
            f"User {current_user.email} deleted database connection '{connection_name}' "
            f"from team {current_team.name}"
        )

        return MessageResponse(
            message=f"Database connection '{connection_name}' deleted successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete database connection"
        )


# =============================================================================
# TEST CONNECTION
# =============================================================================


@router.post(
    "/test",
    response_model=DatabaseConnectionTestResponse,
    summary="Test database connection",
    description="Test a database connection without saving it"
)
async def test_connection_endpoint(
    request: DatabaseConnectionTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Test a database connection without saving it.

    Useful for validating credentials before creating a connection.
    """
    return test_database_connection(
        db_type=request.db_type,
        host=request.host,
        port=request.port,
        database_name=request.database_name,
        username=request.username,
        password=request.password,
        ssl_enabled=request.ssl_enabled
    )


@router.post(
    "/{connection_id}/test",
    response_model=DatabaseConnectionTestResponse,
    summary="Test existing connection",
    description="Test an existing database connection"
)
async def test_existing_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Test an existing database connection.

    Decrypts the stored password and attempts to connect.
    Updates last_connected_at on success.
    """
    try:
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        # Decrypt password
        decrypted_password = decrypt_db_password(connection.encrypted_password)

        # Test connection
        result = test_database_connection(
            db_type=connection.db_type,
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name,
            username=connection.username,
            password=decrypted_password,
            ssl_enabled=connection.ssl_enabled
        )

        # Update last_connected_at if successful
        if result.success:
            connection.last_connected_at = datetime.utcnow()
            db.commit()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test database connection: {str(e)}"
        )


# =============================================================================
# AGENT TOKEN MANAGEMENT
# =============================================================================


@router.post(
    "/{connection_id}/rotate-token",
    response_model=MessageResponse,
    summary="Rotate agent token",
    description="Regenerate the agent token for a database connection (requires OWNER or ADMIN role)",
    dependencies=[Depends(require_role(["OWNER", "ADMIN"]))]
)
async def rotate_agent_token(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Rotate (regenerate) the agent token for a database connection.

    This will invalidate the old token. Collectors using the old token
    will need to be updated with the new token.

    Requires OWNER or ADMIN role.
    """
    try:
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        # Rotate the token
        old_token_preview = connection.mask_agent_token()
        connection.rotate_agent_token()

        db.commit()
        db.refresh(connection)

        logger.warning(
            f"User {current_user.email} rotated agent token for '{connection.name}' "
            f"(old: {old_token_preview}, new: {connection.mask_agent_token()})"
        )

        return MessageResponse(
            message=f"Agent token rotated successfully. Old token is now invalid. New token: {connection.mask_agent_token()}"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rotating agent token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate agent token"
        )


@router.get(
    "/{connection_id}/agent-token",
    summary="Get full agent token",
    description="Get the full agent token for a database connection (requires OWNER or ADMIN role)",
    dependencies=[Depends(require_role(["OWNER", "ADMIN"]))]
)
async def get_agent_token(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get the full agent token for a database connection.

    Use this to copy/paste the token for collector configuration.
    Be careful not to expose this token publicly.

    Requires OWNER or ADMIN role.
    """
    try:
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.team_id == current_team.id
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )

        if not connection.agent_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No agent token found for this connection"
            )

        logger.info(
            f"User {current_user.email} retrieved agent token for '{connection.name}'"
        )

        return {
            "agent_token": connection.agent_token,
            "created_at": connection.agent_token_created_at.isoformat() if connection.agent_token_created_at else None,
            "connection_name": connection.name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving agent token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent token"
        )
