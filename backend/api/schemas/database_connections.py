"""
Pydantic schemas for database connections API.

Defines request and response models for managing database connections.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


# =============================================================================
# DATABASE CONNECTION REQUEST SCHEMAS
# =============================================================================


class DatabaseConnectionCreateRequest(BaseModel):
    """Request schema for creating a database connection."""
    name: str = Field(..., min_length=1, max_length=255, description="Connection name")
    db_type: str = Field(..., description="Database type: mysql, postgres, oracle, sqlserver")
    host: str = Field(..., min_length=1, max_length=255, description="Database host")
    port: int = Field(..., ge=1, le=65535, description="Database port (1-65535)")
    database_name: str = Field(..., min_length=1, max_length=100, description="Database name")
    username: str = Field(..., min_length=1, max_length=100, description="Database username")
    password: str = Field(..., min_length=1, description="Database password (will be encrypted)")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS connection")
    ssl_ca: Optional[str] = Field(None, description="SSL CA certificate (PEM format)")
    visibility_scope: Optional[str] = Field(
        default='TEAM_ONLY',
        description="Visibility scope: TEAM_ONLY, ORG_WIDE, or USER_ONLY"
    )

    @field_validator('db_type')
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        """Validate database type."""
        allowed_types = ['mysql', 'postgres', 'postgresql', 'oracle', 'sqlserver']
        v_lower = v.lower()
        if v_lower not in allowed_types:
            raise ValueError(f"db_type must be one of: {', '.join(allowed_types)}")
        # Normalize postgresql to postgres
        return 'postgres' if v_lower == 'postgresql' else v_lower

    @field_validator('visibility_scope')
    @classmethod
    def validate_visibility_scope(cls, v: Optional[str]) -> str:
        """Validate visibility scope."""
        if v is None:
            return 'TEAM_ONLY'
        allowed_scopes = ['TEAM_ONLY', 'ORG_WIDE', 'USER_ONLY']
        v_upper = v.upper()
        if v_upper not in allowed_scopes:
            raise ValueError(f"visibility_scope must be one of: {', '.join(allowed_scopes)}")
        return v_upper

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production MySQL",
                "db_type": "mysql",
                "host": "db.example.com",
                "port": 3306,
                "database_name": "myapp",
                "username": "monitor_user",
                "password": "secure_password",
                "ssl_enabled": True
            }
        }
    )


class DatabaseConnectionUpdateRequest(BaseModel):
    """Request schema for updating a database connection."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connection name")
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="Database host")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Database port")
    database_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Database name")
    username: Optional[str] = Field(None, min_length=1, max_length=100, description="Database username")
    password: Optional[str] = Field(None, min_length=1, description="New password (will be encrypted)")
    ssl_enabled: Optional[bool] = Field(None, description="Enable SSL/TLS connection")
    ssl_ca: Optional[str] = Field(None, description="SSL CA certificate (PEM format)")
    visibility_scope: Optional[str] = Field(None, description="Visibility scope: TEAM_ONLY, ORG_WIDE, or USER_ONLY")
    is_active: Optional[bool] = Field(None, description="Enable/disable connection")

    @field_validator('visibility_scope')
    @classmethod
    def validate_visibility_scope(cls, v: Optional[str]) -> Optional[str]:
        """Validate visibility scope."""
        if v is None:
            return None
        allowed_scopes = ['TEAM_ONLY', 'ORG_WIDE', 'USER_ONLY']
        v_upper = v.upper()
        if v_upper not in allowed_scopes:
            raise ValueError(f"visibility_scope must be one of: {', '.join(allowed_scopes)}")
        return v_upper

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production MySQL Updated",
                "is_active": True
            }
        }
    )


class DatabaseConnectionTestRequest(BaseModel):
    """Request schema for testing a database connection."""
    db_type: str = Field(..., description="Database type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., ge=1, le=65535, description="Database port")
    database_name: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")

    @field_validator('db_type')
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        """Validate database type."""
        allowed_types = ['mysql', 'postgres', 'postgresql', 'oracle', 'sqlserver']
        v_lower = v.lower()
        if v_lower not in allowed_types:
            raise ValueError(f"db_type must be one of: {', '.join(allowed_types)}")
        return 'postgres' if v_lower == 'postgresql' else v_lower


# =============================================================================
# DATABASE CONNECTION RESPONSE SCHEMAS
# =============================================================================


class DatabaseConnectionResponse(BaseModel):
    """Response schema for database connection."""
    id: UUID = Field(..., description="Connection ID")
    team_id: UUID = Field(..., description="Team ID")
    organization_id: Optional[UUID] = Field(None, description="Organization ID")
    name: str = Field(..., description="Connection name")
    db_type: str = Field(..., description="Database type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database_name: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    # Note: password is NEVER returned in responses

    # Agent authentication (masked for security)
    agent_token: Optional[str] = Field(None, description="Agent token (full - only for internal use)")
    agent_token_created_at: Optional[datetime] = Field(None, description="Agent token creation/rotation timestamp")

    # Visibility and ownership
    visibility_scope: str = Field(..., description="Visibility scope: TEAM_ONLY, ORG_WIDE, or USER_ONLY")
    owner_user_id: Optional[UUID] = Field(None, description="User who created this connection")
    is_legacy: bool = Field(default=False, description="True if auto-created during data migration")

    ssl_enabled: bool = Field(..., description="SSL/TLS enabled")
    is_active: bool = Field(..., description="Connection is active")
    last_connected_at: Optional[datetime] = Field(None, description="Last successful connection")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def agent_token_masked(self) -> Optional[str]:
        """Return masked agent token for display (show only last 8 chars)."""
        if not self.agent_token:
            return None
        if len(self.agent_token) <= 12:
            return self.agent_token[:4] + '****'
        return self.agent_token[:8] + '****' + self.agent_token[-8:]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "team_id": "660e8400-e29b-41d4-a716-446655440001",
                "organization_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Production MySQL",
                "db_type": "mysql",
                "host": "db.example.com",
                "port": 3306,
                "database_name": "myapp",
                "username": "monitor_user",
                "agent_token_masked": "agt_1234****abcd5678",
                "agent_token_created_at": "2025-11-01T08:00:00Z",
                "visibility_scope": "TEAM_ONLY",
                "owner_user_id": "880e8400-e29b-41d4-a716-446655440003",
                "is_legacy": False,
                "ssl_enabled": True,
                "is_active": True,
                "last_connected_at": "2025-11-01T10:30:00Z",
                "created_at": "2025-11-01T08:00:00Z",
                "updated_at": "2025-11-01T10:30:00Z"
            }
        }
    )


class DatabaseConnectionTestResponse(BaseModel):
    """Response schema for database connection test."""
    success: bool = Field(..., description="Test successful")
    message: str = Field(..., description="Test result message")
    server_version: Optional[str] = Field(None, description="Database server version")
    latency_ms: Optional[float] = Field(None, description="Connection latency in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Connection successful",
                "server_version": "8.0.35",
                "latency_ms": 12.5
            }
        }
    )


class DatabaseConnectionListResponse(BaseModel):
    """Response schema for list of database connections."""
    total: int = Field(..., description="Total number of connections")
    connections: list[DatabaseConnectionResponse] = Field(..., description="List of connections")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 2,
                "connections": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "team_id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Production MySQL",
                        "db_type": "mysql",
                        "host": "db.example.com",
                        "port": 3306,
                        "database_name": "myapp",
                        "username": "monitor_user",
                        "ssl_enabled": True,
                        "is_active": True,
                        "last_connected_at": "2025-11-01T10:30:00Z",
                        "created_at": "2025-11-01T08:00:00Z",
                        "updated_at": "2025-11-01T10:30:00Z"
                    }
                ]
            }
        }
    )
