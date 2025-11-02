"""
Pydantic schemas for onboarding API.

Defines request and response models for the onboarding wizard flow.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


# =============================================================================
# ONBOARDING REQUEST SCHEMAS
# =============================================================================


class OnboardingStartRequest(BaseModel):
    """Request schema for starting the onboarding process."""
    organization_name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    organization_slug: Optional[str] = Field(None, min_length=1, max_length=100, description="URL-friendly identifier (auto-generated if not provided)")
    team_name: str = Field(..., min_length=1, max_length=255, description="Team name")
    collector_name: str = Field(..., min_length=1, max_length=255, description="Collector name/label")
    collector_hostname: Optional[str] = Field(None, max_length=255, description="Collector hostname (optional)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "organization_name": "Acme Corp",
                "organization_slug": "acme-corp",
                "team_name": "Production Team",
                "collector_name": "Production Collector",
                "collector_hostname": "collector-prod-01"
            }
        }
    )


class DatabaseConfigRequest(BaseModel):
    """Request schema for adding a database to the collector."""
    name: str = Field(..., min_length=1, max_length=255, description="Database connection name")
    db_type: str = Field(..., description="Database type: mysql or postgres")
    host: str = Field(..., min_length=1, max_length=255, description="Database host")
    port: int = Field(..., ge=1, le=65535, description="Database port (1-65535)")
    database_name: str = Field(..., min_length=1, max_length=100, description="Database name")
    username: str = Field(..., min_length=1, max_length=100, description="Database username")
    password: str = Field(..., min_length=1, description="Database password (will be encrypted)")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS connection")
    ssl_ca: Optional[str] = Field(None, description="SSL CA certificate (PEM format)")

    @field_validator('db_type')
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        """Validate database type."""
        allowed_types = ['mysql', 'postgres', 'postgresql']
        v_lower = v.lower()
        if v_lower not in allowed_types:
            raise ValueError(f"db_type must be one of: {', '.join(allowed_types)}")
        # Normalize postgresql to postgres
        return 'postgres' if v_lower == 'postgresql' else v_lower

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production MySQL",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database_name": "myapp",
                "username": "monitor_user",
                "password": "secure_password",
                "ssl_enabled": False
            }
        }
    )


class OnboardingDatabasesRequest(BaseModel):
    """Request schema for adding databases during onboarding."""
    collector_id: UUID = Field(..., description="Collector ID from onboarding start")
    databases: List[DatabaseConfigRequest] = Field(..., min_length=1, description="List of database configurations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "collector_id": "550e8400-e29b-41d4-a716-446655440000",
                "databases": [
                    {
                        "name": "Production MySQL",
                        "db_type": "mysql",
                        "host": "localhost",
                        "port": 3306,
                        "database_name": "myapp",
                        "username": "monitor_user",
                        "password": "secure_password"
                    }
                ]
            }
        }
    )


class OnboardingCompleteRequest(BaseModel):
    """Request schema for marking onboarding as complete."""
    collector_id: UUID = Field(..., description="Collector ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "collector_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


# =============================================================================
# ONBOARDING RESPONSE SCHEMAS
# =============================================================================


class OnboardingStartResponse(BaseModel):
    """Response schema for starting onboarding."""
    success: bool = Field(..., description="Operation successful")
    organization_id: UUID = Field(..., description="Created organization ID")
    team_id: UUID = Field(..., description="Created team ID")
    collector_id: UUID = Field(..., description="Created collector ID")
    agent_token: str = Field(..., description="Generated agent token for collector authentication")
    docker_command: str = Field(..., description="Docker run command for the customer to execute")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "organization_id": "770e8400-e29b-41d4-a716-446655440002",
                "team_id": "660e8400-e29b-41d4-a716-446655440001",
                "collector_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_token": "agt_1234567890abcdefghijklmnopqrstuvwxyz",
                "docker_command": "docker run -d --name dbpower-agent -e DBPOWER_API_URL=https://api.dbpower.io -e DBPOWER_AGENT_TOKEN=agt_xxx humanaise/dbpower-agent:latest"
            }
        }
    )


class DatabaseConnectionStatus(BaseModel):
    """Database connection status for onboarding."""
    id: UUID = Field(..., description="Database connection ID")
    name: str = Field(..., description="Connection name")
    db_type: str = Field(..., description="Database type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database_name: str = Field(..., description="Database name")
    status: str = Field(..., description="Connection status: PENDING, CONNECTED, ERROR")
    last_connected_at: Optional[datetime] = Field(None, description="Last successful connection")
    error_message: Optional[str] = Field(None, description="Error message if status is ERROR")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "name": "Production MySQL",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database_name": "myapp",
                "status": "CONNECTED",
                "last_connected_at": "2025-11-02T10:30:00Z",
                "error_message": None
            }
        }
    )


class OnboardingStatusResponse(BaseModel):
    """Response schema for onboarding status."""
    collector_id: UUID = Field(..., description="Collector ID")
    collector_name: str = Field(..., description="Collector name")
    collector_status: str = Field(..., description="Collector status: ACTIVE, INACTIVE, ERROR")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat from collector")
    databases: List[DatabaseConnectionStatus] = Field(..., description="Database connections")
    total_databases: int = Field(..., description="Total number of databases configured")
    connected_databases: int = Field(..., description="Number of databases successfully connected")
    pending_databases: int = Field(..., description="Number of databases pending connection")
    error_databases: int = Field(..., description="Number of databases with errors")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "collector_id": "550e8400-e29b-41d4-a716-446655440000",
                "collector_name": "Production Collector",
                "collector_status": "ACTIVE",
                "last_heartbeat": "2025-11-02T10:35:00Z",
                "databases": [],
                "total_databases": 2,
                "connected_databases": 2,
                "pending_databases": 0,
                "error_databases": 0
            }
        }
    )


class OnboardingDatabasesResponse(BaseModel):
    """Response schema for adding databases during onboarding."""
    success: bool = Field(..., description="Operation successful")
    databases_added: int = Field(..., description="Number of databases successfully added")
    databases_failed: int = Field(default=0, description="Number of databases that failed")
    database_ids: List[UUID] = Field(..., description="List of created database connection IDs")
    errors: List[str] = Field(default_factory=list, description="Error messages (if any)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "databases_added": 2,
                "databases_failed": 0,
                "database_ids": [
                    "880e8400-e29b-41d4-a716-446655440003",
                    "990e8400-e29b-41d4-a716-446655440004"
                ],
                "errors": []
            }
        }
    )


class OnboardingCompleteResponse(BaseModel):
    """Response schema for completing onboarding."""
    success: bool = Field(..., description="Onboarding completed successfully")
    message: str = Field(..., description="Completion message")
    collector_id: UUID = Field(..., description="Collector ID")
    collector_status: str = Field(..., description="Final collector status")
    databases_configured: int = Field(..., description="Total databases configured")
    next_steps: List[str] = Field(..., description="Recommended next steps")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Onboarding completed successfully! Your collector is now monitoring 2 databases.",
                "collector_id": "550e8400-e29b-41d4-a716-446655440000",
                "collector_status": "ACTIVE",
                "databases_configured": 2,
                "next_steps": [
                    "View your dashboard to see collected queries",
                    "Configure alerts for critical slow queries",
                    "Review AI-powered optimization suggestions"
                ]
            }
        }
    )
