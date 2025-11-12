"""
Audit logging middleware.
Records all API requests and significant actions for compliance.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from sqlalchemy.orm import Session
from typing import Optional, Callable
from datetime import datetime
import json
import time

from db.models_multitenant import AuditLog, SessionLocal, User, Organization


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests for audit purposes.

    Logs:
    - Who: user_id or organization_id
    - What: HTTP method, path, action
    - When: timestamp
    - Where: IP address, user agent
    - Result: status code, error message
    """

    # Paths to exclude from audit logging (health checks, static files, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc"
    }

    # Sensitive headers to redact in logs
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "cookie",
        "x-csrf-token"
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit trail."""
        start_time = time.time()

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Extract request information
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Try to extract authentication info
        user_id = None
        org_id = None

        # Check for user authentication (JWT)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            user_id = self._extract_user_id_from_token(auth_header.replace("Bearer ", ""))

        # Check for organization authentication (API Key)
        api_key = request.headers.get("x-api-key")
        if api_key:
            org_id = self._extract_org_id_from_api_key(api_key)

        # Store auth info in request state for downstream use
        request.state.audit_user_id = user_id
        request.state.audit_org_id = org_id

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Determine action from method and path
        action = self._determine_action(request.method, request.url.path)

        # Extract resource type and ID from path
        resource_type, resource_id = self._extract_resource_info(request.url.path)

        # Log audit entry (async in background)
        try:
            self._create_audit_log(
                organization_id=org_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request.method,
                request_path=request.url.path,
                status_code=response.status_code,
                error_message=None if response.status_code < 400 else f"HTTP {response.status_code}",
                details={
                    "duration_ms": round(duration * 1000, 2),
                    "query_params": dict(request.query_params) if request.query_params else {}
                }
            )
        except Exception as e:
            # Don't fail request if audit logging fails
            print(f"⚠️ Audit logging failed: {e}")

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _extract_user_id_from_token(self, token: str) -> Optional[int]:
        """Extract user ID from JWT token."""
        try:
            from core.security import decode_token
            payload = decode_token(token)
            if payload:
                return payload.get("user_id")
        except Exception:
            pass
        return None

    def _extract_org_id_from_api_key(self, api_key: str) -> Optional[int]:
        """Extract organization ID from API key format."""
        try:
            from core.security import extract_org_id_from_api_key
            return extract_org_id_from_api_key(api_key)
        except Exception:
            pass
        return None

    def _determine_action(self, method: str, path: str) -> str:
        """
        Determine action from HTTP method and path.

        Examples:
        - POST /api/v1/slow-queries -> "slow_query.create"
        - GET /api/v1/slow-queries/123 -> "slow_query.read"
        - PATCH /api/v1/slow-queries/123/status -> "slow_query.update_status"
        - DELETE /api/v1/users/123 -> "user.delete"
        """
        path_parts = [p for p in path.split("/") if p]

        # Extract resource name
        resource = "unknown"
        if len(path_parts) >= 3:
            resource = path_parts[2].replace("-", "_")  # Convert slow-queries to slow_queries

        # Map HTTP method to action
        method_map = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }
        action_verb = method_map.get(method, method.lower())

        # Check for sub-actions (e.g., /slow-queries/123/analyze)
        if len(path_parts) >= 5:
            sub_action = path_parts[4]
            return f"{resource}.{sub_action}"

        return f"{resource}.{action_verb}"

    def _extract_resource_info(self, path: str) -> tuple[Optional[str], Optional[int]]:
        """
        Extract resource type and ID from path.

        Examples:
        - /api/v1/slow-queries/123 -> ("slow_query", 123)
        - /api/v1/users/456/teams -> ("user", 456)
        """
        path_parts = [p for p in path.split("/") if p]

        resource_type = None
        resource_id = None

        # Extract resource type (e.g., slow-queries -> slow_query)
        if len(path_parts) >= 3:
            resource_type = path_parts[2].replace("-", "_").rstrip("s")  # Remove plural

        # Extract resource ID (first numeric part after resource name)
        if len(path_parts) >= 4:
            try:
                resource_id = int(path_parts[3])
            except ValueError:
                pass

        return (resource_type, resource_id)

    def _create_audit_log(
        self,
        organization_id: Optional[int],
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[int],
        ip_address: str,
        user_agent: str,
        request_method: str,
        request_path: str,
        status_code: int,
        error_message: Optional[str],
        details: dict
    ):
        """Create audit log entry in database."""
        db = SessionLocal()
        try:
            audit_log = AuditLog(
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,  # Truncate long user agents
                request_method=request_method,
                request_path=request_path[:500] if request_path else None,
                status_code=status_code,
                error_message=error_message,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create audit log: {e}")
        finally:
            db.close()


# ============================================================================
# AUDIT LOGGING HELPERS (for explicit logging)
# ============================================================================

def log_audit_event(
    db: Session,
    action: str,
    user: Optional[User] = None,
    organization: Optional[Organization] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    status_code: int = 200,
    error_message: Optional[str] = None
):
    """
    Manually log an audit event.

    Use this for important actions that happen outside of HTTP requests
    (e.g., background tasks, scheduled jobs).

    Usage:
        log_audit_event(
            db=db,
            action="query.auto_analyze",
            organization=org,
            resource_type="slow_query",
            resource_id=query.id,
            details={"trigger": "scheduled_task"}
        )
    """
    try:
        audit_log = AuditLog(
            organization_id=organization.id if organization else None,
            user_id=user.id if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details or {},
            status_code=status_code,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to log audit event: {e}")


def get_audit_logs(
    db: Session,
    organization_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """
    Query audit logs with filters.

    Usage:
        logs = get_audit_logs(
            db=db,
            organization_id=123,
            action="user.login",
            start_date=datetime(2024, 1, 1),
            limit=50
        )
    """
    query = db.query(AuditLog)

    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)

    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    query = query.order_by(AuditLog.timestamp.desc())
    query = query.offset(offset).limit(limit)

    return query.all()


def get_audit_stats(
    db: Session,
    organization_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """
    Get audit log statistics.

    Returns:
        {
            "total_requests": int,
            "by_action": {"action": count, ...},
            "by_status": {200: count, 404: count, ...},
            "by_user": {user_id: count, ...}
        }
    """
    from sqlalchemy import func

    query = db.query(AuditLog)

    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)

    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    # Total requests
    total = query.count()

    # By action
    by_action = {}
    action_counts = db.query(
        AuditLog.action,
        func.count(AuditLog.id)
    ).group_by(AuditLog.action)

    if organization_id:
        action_counts = action_counts.filter(AuditLog.organization_id == organization_id)
    if start_date:
        action_counts = action_counts.filter(AuditLog.timestamp >= start_date)
    if end_date:
        action_counts = action_counts.filter(AuditLog.timestamp <= end_date)

    for action, count in action_counts.all():
        by_action[action] = count

    # By status code
    by_status = {}
    status_counts = db.query(
        AuditLog.status_code,
        func.count(AuditLog.id)
    ).group_by(AuditLog.status_code)

    if organization_id:
        status_counts = status_counts.filter(AuditLog.organization_id == organization_id)
    if start_date:
        status_counts = status_counts.filter(AuditLog.timestamp >= start_date)
    if end_date:
        status_counts = status_counts.filter(AuditLog.timestamp <= end_date)

    for status, count in status_counts.all():
        by_status[status] = count

    # By user
    by_user = {}
    user_counts = db.query(
        AuditLog.user_id,
        func.count(AuditLog.id)
    ).filter(AuditLog.user_id.isnot(None)).group_by(AuditLog.user_id)

    if organization_id:
        user_counts = user_counts.filter(AuditLog.organization_id == organization_id)
    if start_date:
        user_counts = user_counts.filter(AuditLog.timestamp >= start_date)
    if end_date:
        user_counts = user_counts.filter(AuditLog.timestamp <= end_date)

    for user_id, count in user_counts.all():
        by_user[user_id] = count

    return {
        "total_requests": total,
        "by_action": by_action,
        "by_status": by_status,
        "by_user": by_user
    }
