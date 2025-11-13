"""
Collector Agent Management API.

Endpoints for managing collector agents that monitor external databases.
Collectors are separate processes/containers that authenticate and communicate
with the backend via API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta

from db.models_multitenant import (
    Collector, CollectorCommand, CollectorStatus, CollectorType,
    User, get_db, UserRole
)
from middleware.auth import (
    get_current_user,
    get_collector_from_api_key,
    check_collector_access,
    require_org_admin
)
from core.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/collectors", tags=["Collector Agents"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CollectorCreateRequest(BaseModel):
    """Request to create/register a new collector."""
    name: str = Field(..., min_length=1, max_length=255, description="Collector name")
    type: CollectorType = Field(..., description="Database type (mysql or postgres)")
    team_id: int = Field(..., description="Team ID this collector belongs to")
    config: dict = Field(..., description="Database connection configuration")
    collection_interval_minutes: int = Field(5, ge=1, le=1440, description="Collection interval in minutes")
    auto_collect: bool = Field(True, description="Enable automatic collection")


class CollectorUpdateRequest(BaseModel):
    """Request to update collector configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict] = None
    collection_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    auto_collect: Optional[bool] = None


class CollectorResponse(BaseModel):
    """Collector response model."""
    id: int
    organization_id: int
    team_id: int
    name: str
    type: str
    status: str
    config: dict
    last_heartbeat: Optional[datetime]
    last_collection: Optional[datetime]
    last_error: Optional[str]
    stats: dict
    collection_interval_minutes: int
    auto_collect: bool
    is_online: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CollectorListResponse(BaseModel):
    """List of collectors response."""
    collectors: List[CollectorResponse]
    total: int


class HeartbeatRequest(BaseModel):
    """Heartbeat request from collector agent."""
    stats: Optional[dict] = Field(default={}, description="Current statistics")
    error: Optional[str] = Field(None, description="Last error message if any")


class HeartbeatResponse(BaseModel):
    """Heartbeat response with pending commands."""
    status: str
    message: str
    commands: List[dict]


class CollectorCommandResponse(BaseModel):
    """Collector command response."""
    id: int
    command: str
    params: dict
    executed: bool
    executed_at: Optional[datetime]
    result: dict
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class CommandExecutionRequest(BaseModel):
    """Command execution result from collector."""
    command_id: int
    success: bool
    result: dict = Field(default={})


# ============================================================================
# COLLECTOR REGISTRATION & AUTHENTICATION
# ============================================================================

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_collector(
    request: CollectorCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a new collector agent.

    Only ORG_ADMIN and SUPER_ADMIN can register collectors.

    Returns the collector ID and API key (SAVE IT - shown only once!).
    """
    # Check permissions
    if user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can register collectors"
        )

    # Verify team belongs to user's organization
    from db.models_multitenant import Team
    team = db.query(Team).filter(Team.id == request.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if user.role != UserRole.SUPER_ADMIN and team.organization_id != user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team does not belong to your organization"
        )

    # Check for duplicate name
    existing = db.query(Collector).filter(
        Collector.organization_id == team.organization_id,
        Collector.name == request.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collector with name '{request.name}' already exists in this organization"
        )

    # Create collector
    collector = Collector(
        organization_id=team.organization_id,
        team_id=request.team_id,
        name=request.name,
        type=request.type,
        status=CollectorStatus.STARTING,
        config=request.config,
        collection_interval_minutes=request.collection_interval_minutes,
        auto_collect=request.auto_collect,
        api_key_hash="",  # Will be set by generate_api_key
        stats={}
    )

    db.add(collector)
    db.flush()  # Get collector.id

    # Generate API key
    api_key = collector.generate_api_key()
    db.commit()

    logger.info(f"Collector registered: {collector.name} (ID: {collector.id}, Org: {team.organization_id})")

    return {
        "id": collector.id,
        "name": collector.name,
        "type": collector.type.value,
        "api_key": api_key,
        "message": "Collector registered successfully. SAVE THE API KEY - it will not be shown again!",
        "organization_id": collector.organization_id,
        "team_id": collector.team_id
    }


@router.post("/{collector_id}/heartbeat", response_model=HeartbeatResponse)
async def collector_heartbeat(
    collector_id: int,
    heartbeat_data: HeartbeatRequest,
    collector: Collector = Depends(get_collector_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Collector heartbeat endpoint.

    Collectors should send heartbeats every 30 seconds.
    Returns any pending commands for the collector to execute.
    """
    # Verify collector ID matches authenticated collector
    if collector.id != collector_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collector ID mismatch"
        )

    # Update heartbeat
    collector.last_heartbeat = datetime.utcnow()
    collector.status = CollectorStatus.ONLINE

    # Update stats if provided
    if heartbeat_data.stats:
        collector.stats = {**collector.stats, **heartbeat_data.stats}

    # Update error if provided
    if heartbeat_data.error:
        collector.last_error = heartbeat_data.error
        collector.status = CollectorStatus.ERROR

    db.commit()

    # Fetch pending commands
    pending_commands = db.query(CollectorCommand).filter(
        CollectorCommand.collector_id == collector_id,
        CollectorCommand.executed == False,
        CollectorCommand.expires_at > datetime.utcnow()
    ).all()

    commands_list = [
        {
            "id": cmd.id,
            "command": cmd.command,
            "params": cmd.params,
            "created_at": cmd.created_at.isoformat()
        }
        for cmd in pending_commands
    ]

    return HeartbeatResponse(
        status="ok",
        message="Heartbeat received",
        commands=commands_list
    )


@router.post("/{collector_id}/commands/{command_id}/execute")
async def report_command_execution(
    collector_id: int,
    command_id: int,
    execution: CommandExecutionRequest,
    collector: Collector = Depends(get_collector_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Report command execution result.

    Collector agents call this after executing a command.
    """
    # Verify collector ID
    if collector.id != collector_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collector ID mismatch"
        )

    # Fetch command
    command = db.query(CollectorCommand).filter(
        CollectorCommand.id == command_id,
        CollectorCommand.collector_id == collector_id
    ).first()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    # Update command status
    command.executed = True
    command.executed_at = datetime.utcnow()
    command.result = {
        "success": execution.success,
        **execution.result
    }

    db.commit()

    return {
        "status": "ok",
        "message": "Command execution recorded"
    }


# ============================================================================
# COLLECTOR MANAGEMENT (USER API)
# ============================================================================

@router.get("", response_model=CollectorListResponse)
async def list_collectors(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all collectors accessible to the current user.

    - SUPER_ADMIN: All collectors
    - ORG_ADMIN: Collectors in their organization
    - TEAM_LEAD: Collectors in their team
    - USER: No access
    """
    if user.role == UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users cannot access collector management"
        )

    # Build query based on role
    query = db.query(Collector)

    if user.role == UserRole.SUPER_ADMIN:
        pass  # No filter, see all
    elif user.role == UserRole.ORG_ADMIN:
        query = query.filter(Collector.organization_id == user.organization_id)
    elif user.role == UserRole.TEAM_LEAD:
        # Get user's team
        from db.models_multitenant import Identity
        identity = db.query(Identity).filter(Identity.id == user.identity_id).first()
        if not identity:
            return CollectorListResponse(collectors=[], total=0)
        query = query.filter(Collector.team_id == identity.team_id)

    collectors = query.order_by(Collector.created_at.desc()).all()

    # Add is_online status
    collector_responses = []
    for collector in collectors:
        collector_dict = {
            "id": collector.id,
            "organization_id": collector.organization_id,
            "team_id": collector.team_id,
            "name": collector.name,
            "type": collector.type.value,
            "status": collector.status.value,
            "config": collector.config,
            "last_heartbeat": collector.last_heartbeat,
            "last_collection": collector.last_collection,
            "last_error": collector.last_error,
            "stats": collector.stats,
            "collection_interval_minutes": collector.collection_interval_minutes,
            "auto_collect": collector.auto_collect,
            "is_online": collector.is_online(),
            "created_at": collector.created_at,
            "updated_at": collector.updated_at
        }
        collector_responses.append(CollectorResponse(**collector_dict))

    return CollectorListResponse(
        collectors=collector_responses,
        total=len(collector_responses)
    )


@router.get("/{collector_id}", response_model=CollectorResponse)
async def get_collector(
    collector_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get collector details by ID."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    return CollectorResponse(
        id=collector.id,
        organization_id=collector.organization_id,
        team_id=collector.team_id,
        name=collector.name,
        type=collector.type.value,
        status=collector.status.value,
        config=collector.config,
        last_heartbeat=collector.last_heartbeat,
        last_collection=collector.last_collection,
        last_error=collector.last_error,
        stats=collector.stats,
        collection_interval_minutes=collector.collection_interval_minutes,
        auto_collect=collector.auto_collect,
        is_online=collector.is_online(),
        created_at=collector.created_at,
        updated_at=collector.updated_at
    )


@router.patch("/{collector_id}", response_model=CollectorResponse)
async def update_collector(
    collector_id: int,
    update_data: CollectorUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update collector configuration."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    # Update fields
    if update_data.name is not None:
        collector.name = update_data.name
    if update_data.config is not None:
        collector.config = update_data.config
    if update_data.collection_interval_minutes is not None:
        collector.collection_interval_minutes = update_data.collection_interval_minutes
    if update_data.auto_collect is not None:
        collector.auto_collect = update_data.auto_collect

    collector.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Collector {collector_id} updated by user {user.id}")

    return CollectorResponse(
        id=collector.id,
        organization_id=collector.organization_id,
        team_id=collector.team_id,
        name=collector.name,
        type=collector.type.value,
        status=collector.status.value,
        config=collector.config,
        last_heartbeat=collector.last_heartbeat,
        last_collection=collector.last_collection,
        last_error=collector.last_error,
        stats=collector.stats,
        collection_interval_minutes=collector.collection_interval_minutes,
        auto_collect=collector.auto_collect,
        is_online=collector.is_online(),
        created_at=collector.created_at,
        updated_at=collector.updated_at
    )


@router.delete("/{collector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collector(
    collector_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a collector."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    logger.info(f"Collector {collector_id} ({collector.name}) deleted by user {user.id}")

    db.delete(collector)
    db.commit()

    return None


# ============================================================================
# COLLECTOR COMMANDS
# ============================================================================

@router.post("/{collector_id}/start")
async def start_collector(
    collector_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send START command to collector."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    # Create command
    command = CollectorCommand(
        collector_id=collector_id,
        command="start",
        params={},
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(command)
    db.commit()

    logger.info(f"START command sent to collector {collector_id} by user {user.id}")

    return {
        "status": "ok",
        "message": "START command sent to collector",
        "command_id": command.id
    }


@router.post("/{collector_id}/stop")
async def stop_collector(
    collector_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send STOP command to collector."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    # Create command
    command = CollectorCommand(
        collector_id=collector_id,
        command="stop",
        params={},
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(command)

    # Update status
    collector.status = CollectorStatus.STOPPED
    db.commit()

    logger.info(f"STOP command sent to collector {collector_id} by user {user.id}")

    return {
        "status": "ok",
        "message": "STOP command sent to collector",
        "command_id": command.id
    }


@router.post("/{collector_id}/collect")
async def trigger_collection(
    collector_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send COLLECT command to collector (manual trigger)."""
    check_collector_access(user, collector_id, db)

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    # Create command
    command = CollectorCommand(
        collector_id=collector_id,
        command="collect",
        params={"manual": True},
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(command)
    db.commit()

    logger.info(f"COLLECT command sent to collector {collector_id} by user {user.id}")

    return {
        "status": "ok",
        "message": "COLLECT command sent to collector",
        "command_id": command.id
    }


@router.get("/{collector_id}/commands", response_model=List[CollectorCommandResponse])
async def get_collector_commands(
    collector_id: int,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get command history for a collector."""
    check_collector_access(user, collector_id, db)

    commands = db.query(CollectorCommand).filter(
        CollectorCommand.collector_id == collector_id
    ).order_by(CollectorCommand.created_at.desc()).limit(limit).all()

    return [CollectorCommandResponse.model_validate(cmd) for cmd in commands]
