"""
Pydantic schemas for collectors API.

Defines request and response models for collector registration and management.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# COLLECTOR REQUEST SCHEMAS
# =============================================================================


class CollectorRegisterRequest(BaseModel):
    """Request schema for collector registration."""
    agent_token: str = Field(..., min_length=1, description="Agent token for authentication")
    hostname: Optional[str] = Field(None, max_length=255, description="Collector hostname/identifier")
    version: Optional[str] = Field(None, max_length=50, description="Collector software version")
    config_hash: Optional[str] = Field(None, max_length=64, description="Hash of collector configuration")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_token": "agt_1234567890abcdef",
                "hostname": "collector-prod-01",
                "version": "1.0.0",
                "config_hash": "abc123def456"
            }
        }
    )


class CollectorHeartbeatRequest(BaseModel):
    """Request schema for collector heartbeat."""
    status: Optional[str] = Field(None, description="Collector status: ACTIVE, INACTIVE, ERROR")
    metrics: Optional[dict] = Field(None, description="Collector metrics (queries collected, errors, etc.)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ACTIVE",
                "metrics": {
                    "queries_collected": 150,
                    "errors": 0,
                    "uptime_seconds": 3600
                }
            }
        }
    )


# =============================================================================
# COLLECTOR RESPONSE SCHEMAS
# =============================================================================


class CollectorRegisterResponse(BaseModel):
    """Response schema for collector registration."""
    collector_id: UUID = Field(..., description="Collector ID")
    database_connection_id: UUID = Field(..., description="Database connection ID")
    session_token: str = Field(..., description="JWT session token for subsequent requests")
    expires_at: datetime = Field(..., description="Session token expiration")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "collector_id": "550e8400-e29b-41d4-a716-446655440000",
                "database_connection_id": "660e8400-e29b-41d4-a716-446655440001",
                "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-11-02T12:00:00Z"
            }
        }
    )


class CollectorResponse(BaseModel):
    """Response schema for collector details."""
    id: UUID = Field(..., description="Collector ID")
    team_id: UUID = Field(..., description="Team ID")
    organization_id: UUID = Field(..., description="Organization ID")
    name: Optional[str] = Field(None, description="Collector name")
    hostname: Optional[str] = Field(None, description="Collector hostname")
    version: Optional[str] = Field(None, description="Collector version")
    config_hash: Optional[str] = Field(None, description="Configuration hash")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    status: str = Field(..., description="Collector status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "team_id": "660e8400-e29b-41d4-a716-446655440001",
                "organization_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Production Collector",
                "hostname": "collector-prod-01",
                "version": "1.0.0",
                "config_hash": "abc123",
                "last_heartbeat": "2025-11-02T10:30:00Z",
                "status": "ACTIVE",
                "created_at": "2025-11-01T08:00:00Z",
                "updated_at": "2025-11-02T10:30:00Z"
            }
        }
    )


class CollectorListResponse(BaseModel):
    """Response schema for list of collectors."""
    total: int = Field(..., description="Total number of collectors")
    collectors: List[CollectorResponse] = Field(..., description="List of collectors")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 2,
                "collectors": []
            }
        }
    )


# =============================================================================
# INGESTION REQUEST SCHEMAS
# =============================================================================


class SlowQueryIngestionRequest(BaseModel):
    """Single slow query for ingestion."""
    fingerprint: str = Field(..., description="Normalized query pattern")
    full_sql: str = Field(..., description="Full SQL query")
    duration_ms: float = Field(..., description="Query duration in milliseconds")
    rows_examined: Optional[int] = Field(None, description="Rows examined")
    rows_returned: Optional[int] = Field(None, description="Rows returned")
    captured_at: datetime = Field(..., description="When the query was captured")
    plan_json: Optional[dict] = Field(None, description="Execution plan (JSON)")
    plan_text: Optional[str] = Field(None, description="Execution plan (text)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fingerprint": "SELECT * FROM users WHERE id = ?",
                "full_sql": "SELECT * FROM users WHERE id = 123",
                "duration_ms": 1250.5,
                "rows_examined": 10000,
                "rows_returned": 1,
                "captured_at": "2025-11-02T10:30:00Z",
                "plan_json": {"type": "table_scan"},
                "plan_text": "Table scan on users"
            }
        }
    )


class IngestSlowQueriesRequest(BaseModel):
    """Request schema for ingesting slow queries."""
    agent_token: str = Field(..., description="Agent token for authentication")
    queries: List[SlowQueryIngestionRequest] = Field(..., min_length=1, description="List of slow queries")
    metadata: Optional[dict] = Field(None, description="Additional metadata (collector info, etc.)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_token": "agt_1234567890abcdef",
                "queries": [
                    {
                        "fingerprint": "SELECT * FROM users WHERE id = ?",
                        "full_sql": "SELECT * FROM users WHERE id = 123",
                        "duration_ms": 1250.5,
                        "rows_examined": 10000,
                        "rows_returned": 1,
                        "captured_at": "2025-11-02T10:30:00Z"
                    }
                ],
                "metadata": {
                    "collector_version": "1.0.0",
                    "database_version": "8.0.35"
                }
            }
        }
    )


class IngestSlowQueriesResponse(BaseModel):
    """Response schema for slow query ingestion."""
    success: bool = Field(..., description="Ingestion successful")
    queries_received: int = Field(..., description="Number of queries received")
    queries_stored: int = Field(..., description="Number of queries successfully stored")
    queries_skipped: int = Field(default=0, description="Number of queries skipped (duplicates)")
    errors: List[str] = Field(default_factory=list, description="Error messages (if any)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "queries_received": 10,
                "queries_stored": 9,
                "queries_skipped": 1,
                "errors": []
            }
        }
    )
