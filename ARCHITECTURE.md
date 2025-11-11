# DBPower AI Cloud - Architecture

## Overview

DBPower AI Cloud is a **multi-tenant SaaS platform** built as a microservices architecture with 6 core services orchestrated via Docker Compose. The platform enables organizations to collect, analyze, and optimize slow database queries with AI-powered recommendations.

---

## System Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │         External Clients/Users              │
                          └──────────────────┬──────────────────────────┘
                                             │
                                             │ HTTPS (443)
                                             ▼
                          ┌─────────────────────────────────────────────┐
                          │     Admin Panel (React + Nginx)             │
                          │     - Web UI for management                 │
                          │     - Port 3000                             │
                          │     - JWT auth, Protected routes            │
                          └──────────────────┬──────────────────────────┘
                                             │
                                             │ HTTP/JSON
                                             ▼
                          ┌─────────────────────────────────────────────┐
                          │     API Gateway (FastAPI + Redis)           │
                          │     - Rate limiting (100 req/min/org)       │
                          │     - JWT validation                        │
                          │     - Request routing                       │
                          │     - Port 8080                             │
                          └──────────┬─────────────┬────────────────────┘
                                     │             │
                     ┌───────────────┘             └────────────────┐
                     │                                              │
                     │ HTTP/JSON                         HTTP/JSON │
                     ▼                                              ▼
    ┌────────────────────────────────┐          ┌─────────────────────────────┐
    │  Backend API (FastAPI)         │          │  AI Analyzer (FastAPI)      │
    │  - Multi-tenant business logic │          │  - Query analysis           │
    │  - CRUD operations             │◀────────▶│  - OpenAI/Ollama support    │
    │  - Query collection            │          │  - Severity classification  │
    │  - Port 8000                   │          │  - Port 8001                │
    └──────────┬─────────────────────┘          └─────────────────────────────┘
               │
               │ SQL + Redis
               │
       ┌───────┴────────┬───────────────────┐
       │                │                   │
       ▼                ▼                   ▼
┌─────────────┐  ┌──────────────┐  ┌───────────────┐
│ PostgreSQL  │  │    Redis     │  │  Audit Logs   │
│ Multi-Tenant│  │  Rate Limit  │  │  Compliance   │
│ Port 5440   │  │  Port 6379   │  │  (PostgreSQL) │
└─────────────┘  └──────────────┘  └───────────────┘


                          ▲
                          │ HTTP/JSON (Query Submission)
                          │
                ┌─────────┴──────────┐
                │ Client Agents      │
                │ (On-Premise)       │
                │ - MySQL Collector  │
                │ - PostgreSQL       │
                │   Collector        │
                │ - PII Anonymizer   │
                └────────────────────┘
```

---

## Multi-Tenant Data Model

The platform implements a **hierarchical multi-tenant model** with complete data isolation:

```
Organization (Tenant)
    ├── settings: JSON
    ├── api_key: UUID
    ├── Teams[]
    │   ├── name: string
    │   ├── Identities[]
    │   │   ├── name: string
    │   │   └── Users[]
    │   │       ├── email: string (unique globally)
    │   │       ├── role: SUPER_ADMIN | ORG_ADMIN | TEAM_LEAD | USER
    │   │       └── password_hash: bcrypt
    │   └── SlowQueries[]
    │       ├── sql_text: text
    │       ├── execution_time_ms: float
    │       ├── database_type: mysql | postgresql
    │       └── AnalysisResult (1:1)
    │           ├── severity: LOW | MEDIUM | HIGH | CRITICAL
    │           ├── issues: JSON array
    │           └── recommendations: JSON array
    └── AuditLogs[]
        ├── action: string
        ├── resource: string
        └── timestamp: datetime
```

**Key Relationships**:
- **1 Organization** → Many Teams
- **1 Team** → Many Identities
- **1 Identity** → Many Users
- **1 Organization** → Many SlowQueries
- **1 SlowQuery** → 1 AnalysisResult

**Tenant Isolation**:
- Every query automatically filtered by `organization_id`
- Middleware ensures users only access their org's data
- Unique constraints prevent duplicate data within org
- Cascade deletes maintain referential integrity

---

## Authentication & Authorization Flow

### JWT Authentication

```
1. User Login
   ├── POST /api/v1/auth/login {email, password}
   ├── Backend validates credentials (bcrypt)
   ├── Generate JWT access token (30 min) + refresh token (7 days)
   └── Return {access_token, refresh_token, user}

2. Authenticated Request
   ├── Client sends: Authorization: Bearer <access_token>
   ├── API Gateway validates JWT signature
   ├── Extract user_id, org_id, role from token
   ├── Add to request context
   └── Forward to Backend with context

3. Token Refresh
   ├── POST /api/v1/auth/refresh {refresh_token}
   ├── Validate refresh token
   └── Issue new access token
```

### API Key Authentication (Client Agents)

```
1. Organization receives API key on creation
2. Client agent includes: X-API-Key: <org_api_key>
3. Backend validates API key → org_id
4. All queries tagged with org_id
5. Rate limiting applied per org
```

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **SUPER_ADMIN** | Full platform access, create orgs |
| **ORG_ADMIN** | Manage org, teams, users within org |
| **TEAM_LEAD** | View team data, manage team members |
| **USER** | View queries within assigned identity |

**Middleware Enforcement**:
- `@require_role("SUPER_ADMIN")` decorator
- `check_organization_access(user, org_id)` helper
- Automatic filtering by org/team/identity in queries

---

## Request Flow

### Query Analysis Flow

```
1. Client Agent (On-Premise)
   ├── Collects slow query from MySQL/PostgreSQL
   ├── Anonymizes PII (emails, IPs, credit cards)
   ├── Signs request with HMAC-SHA256
   └── POST /api/v1/slow-queries
          Headers: X-API-Key, X-Request-ID, X-Signature

2. API Gateway
   ├── Validates rate limit (100 req/min per org)
   ├── Checks API key → org_id
   ├── Forwards to Backend
   └── Logs request (audit trail)

3. Backend API
   ├── Validates request signature
   ├── Stores SlowQuery record (org_id tagged)
   ├── Returns query_id
   └── Queues for analysis

4. AI Analyzer (Async)
   ├── Backend calls: POST /analyzer/analyze {slow_query_id}
   ├── AI Analyzer retrieves query from DB
   ├── Sends to OpenAI/Ollama
   ├── Parses response → severity, issues, recommendations
   ├── Stores AnalysisResult
   └── Notifies Backend (callback)

5. Admin Panel
   ├── User views Queries page
   ├── Filters: All | Analyzed | Unanalyzed
   ├── Clicks query → Detail panel
   ├── Views AI analysis results
   └── Can trigger re-analysis
```

### Dashboard Statistics Flow

```
1. Admin Panel
   └── GET /api/v1/stats/dashboard

2. API Gateway
   ├── Validates JWT
   ├── Extracts org_id from token
   └── Forwards to Backend

3. Backend
   ├── Queries database filtered by org_id:
   │   - SELECT COUNT(*) FROM slow_queries WHERE org_id = ?
   │   - SELECT COUNT(*) FROM analysis_results WHERE severity = 'CRITICAL' AND org_id = ?
   │   - SELECT AVG(execution_time_ms) FROM slow_queries WHERE org_id = ?
   ├── Aggregates trend data (last 7 days)
   └── Returns JSON: {total_queries, total_issues, avg_time, chart_data}

4. Admin Panel
   ├── Receives statistics
   ├── Updates React state (React Query cache)
   ├── Renders stat cards + Recharts bar chart
   └── Auto-refreshes every 30 seconds
```

---

## Rate Limiting Algorithm

**Token Bucket with Redis Sliding Window**:

```python
Algorithm: rate_limiter.check_limit(org_id)

1. key = f"rate_limit:org:{org_id}"
2. now = time.time()
3. window_start = now - 60  # 1 minute window

4. Redis Pipeline:
   ZREMRANGEBYSCORE key 0 window_start  # Remove expired
   ZCARD key                             # Count current
   ZADD key now now                      # Add current timestamp
   EXPIRE key 120                        # TTL 2 minutes

5. If count >= limit (100):
   - Return 429 Too Many Requests
   - Header: Retry-After: X seconds
6. Else:
   - Allow request
   - Header: X-RateLimit-Remaining: Y
```

**Rate Limits**:
- Per organization: 100 requests/minute, 1000 requests/hour
- Per IP: 200 requests/minute (prevent single IP abuse)
- Distributed across gateway instances via Redis

---

## Security Features

### 1. Authentication Security
- **Password Hashing**: bcrypt with salt (cost factor 12)
- **JWT Signing**: HS256 with 256-bit secret
- **Token Expiry**: Access tokens short-lived (30 min)
- **Refresh Tokens**: Longer-lived (7 days), can be revoked

### 2. Request Security
- **Request Signing**: HMAC-SHA256 prevents replay attacks
- **Request IDs**: Unique UUID per request for audit
- **Timestamp Validation**: Reject requests older than 5 minutes

### 3. Data Security
- **PII Anonymization**: Automatic masking of sensitive data
  - Emails: `user@example.com` → `[EMAIL_REDACTED]`
  - IPs: `192.168.1.1` → `[IP_REDACTED]`
  - Credit Cards: `4532-1234-5678-9010` → `[CREDIT_CARD_REDACTED]`
- **Tenant Isolation**: Middleware enforces org_id filtering
- **Audit Logging**: All actions logged with user/org/resource

### 4. Network Security
- **CORS**: Configurable allowed origins
- **HTTPS**: SSL/TLS termination at load balancer
- **Internal Network**: Services communicate on Docker network
- **Firewall**: Only expose Admin Panel (3000) and API Gateway (8080)

### 5. Compliance
- **Audit Trail**: Immutable logs for SOC 2, GDPR, HIPAA
- **Data Retention**: Configurable query retention (default 90 days)
- **Access Logs**: Request/response logging for security analysis

---

## Deployment Architecture

### Docker Compose Services

```yaml
services:
  internal-db:      # PostgreSQL 15
  redis:            # Redis 7 (cache + rate limiting)
  backend:          # FastAPI (Python 3.11)
  ai-analyzer:      # FastAPI (Python 3.11)
  api-gateway:      # FastAPI (Python 3.11) + Redis client
  admin-panel:      # Nginx Alpine + React 18 build
```

**Dependencies**:
1. `internal-db` & `redis` start first (no dependencies)
2. `backend` waits for `internal-db` & `redis` health checks
3. `ai-analyzer` independent (can start anytime)
4. `api-gateway` waits for `backend`, `ai-analyzer`, `redis`
5. `admin-panel` waits for `api-gateway`

**Health Checks**:
- PostgreSQL: `pg_isready -U ai_core`
- Redis: `redis-cli ping`
- Backend: `curl http://localhost:8000/health`
- AI Analyzer: `curl http://localhost:8001/health`
- API Gateway: `curl http://localhost:8000/health` (internal port)
- Admin Panel: `wget http://localhost/health`

---

## Scaling Strategies

### Horizontal Scaling

**API Gateway** (stateless):
```bash
docker-compose up -d --scale api-gateway=4
```
- Load balancer (e.g., Nginx, Traefik) distributes requests
- Redis ensures consistent rate limiting across instances

**Backend** (stateless):
```bash
docker-compose up -d --scale backend=4
```
- All instances share same PostgreSQL and Redis
- No session affinity required (JWT is stateless)

**AI Analyzer** (stateless):
```bash
docker-compose up -d --scale ai-analyzer=3
```
- Parallel analysis processing
- Backend round-robins requests

### Vertical Scaling

**PostgreSQL**:
- Increase `shared_buffers`, `work_mem`
- Add read replicas for query load
- Use connection pooling (PgBouncer)

**Redis**:
- Increase `maxmemory`
- Use Redis Cluster for larger datasets

**Backend Workers**:
```env
BACKEND_WORKERS=8  # Adjust based on CPU cores
```

### Database Optimization

**Indexes** (already implemented):
- Organizations: `name` (unique)
- Users: `email` (unique), `organization_id`, `team_id`
- SlowQueries: `organization_id`, `sql_fingerprint`, `created_at`
- AnalysisResults: `slow_query_id` (unique)

**Partitioning** (future):
- Partition `slow_queries` by `created_at` (monthly)
- Partition `audit_logs` by `timestamp` (monthly)

---

## Monitoring & Observability

### Service Health

```bash
# All services
curl http://localhost:8080/health  # API Gateway
curl http://localhost:8000/health  # Backend
curl http://localhost:8001/health  # AI Analyzer

# Database
docker-compose exec internal-db pg_isready

# Redis
docker-compose exec redis redis-cli ping
```

### Metrics (Future: Prometheus)

- Request rate (req/sec)
- Error rate (5xx responses)
- Latency (p50, p95, p99)
- Database connection pool utilization
- Redis memory usage
- Active sessions

### Logging

**Structured JSON logs**:
```json
{
  "timestamp": "2025-11-11T10:00:00Z",
  "level": "INFO",
  "service": "api-gateway",
  "request_id": "uuid",
  "user_id": 123,
  "org_id": 1,
  "method": "POST",
  "path": "/api/v1/slow-queries",
  "status": 201,
  "duration_ms": 45
}
```

**Log Aggregation** (Future: ELK Stack):
- Elasticsearch for log storage
- Logstash/Fluentd for log ingestion
- Kibana for visualization

---

## Disaster Recovery

### Backup Strategy

**Database Backups**:
```bash
# Daily automated backups
docker-compose exec -T internal-db pg_dump -U ai_core ai_core | gzip > backup_$(date +%Y%m%d).sql.gz

# Retention: 30 days
# Storage: S3 or equivalent
```

**Redis Backups** (optional):
```bash
docker-compose exec redis redis-cli SAVE
# Copy /data/dump.rdb to backup location
```

### Recovery Procedure

```bash
# 1. Stop services
docker-compose down

# 2. Restore database
gunzip < backup_20250111.sql.gz | docker-compose exec -T internal-db psql -U ai_core ai_core

# 3. Restart services
docker-compose up -d

# 4. Verify health
curl http://localhost:8080/health
```

---

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **Database** | PostgreSQL or SQLite | PostgreSQL (RDS, managed) |
| **JWT Secret** | Default | Generated 256-bit |
| **HTTPS** | HTTP | HTTPS with SSL/TLS |
| **Logging** | DEBUG | INFO or WARNING |
| **Demo Org** | Enabled | Disabled |
| **AI Provider** | Stub (free) | OpenAI or Ollama |
| **Ports** | All exposed | Only 3000, 8080 exposed |
| **Backups** | Manual | Automated daily |
| **Monitoring** | Logs only | Prometheus + Grafana |

---

## Future Enhancements

### Phase 7+
- **WebSocket Support**: Real-time query updates in admin panel
- **Kubernetes Deployment**: Helm charts for K8s
- **Multi-Region**: Database replication across regions
- **Advanced Analytics**: Query trends, cost analysis, recommendations
- **Query Simulator**: Test index changes before production
- **Auto-Remediation**: Automatically create suggested indexes
- **Mobile App**: iOS/Android for monitoring on-the-go
- **Slack/Email Notifications**: Alert on critical issues
- **GraphQL API**: Alternative to REST

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18, TypeScript, Vite | Admin Panel UI |
| **API Gateway** | FastAPI, Redis | Rate limiting, routing |
| **Backend** | FastAPI, SQLAlchemy | Business logic, CRUD |
| **AI** | OpenAI, Ollama | Query analysis |
| **Database** | PostgreSQL 15 | Multi-tenant data |
| **Cache** | Redis 7 | Rate limiting, sessions |
| **Web Server** | Nginx Alpine | Static file serving |
| **Container** | Docker, Docker Compose | Orchestration |
| **Language** | Python 3.11, TypeScript 5 | Backend, Frontend |

---

## Conclusion

DBPower AI Cloud is a **production-ready, scalable, secure** multi-tenant platform designed for enterprise database query optimization. The microservices architecture enables independent scaling, while the multi-tenant model ensures complete data isolation and compliance.

**Key Strengths**:
- ✅ Enterprise-grade security (JWT, RBAC, PII anonymization)
- ✅ Horizontal scaling (stateless services)
- ✅ Multi-provider AI support (cloud + on-premise)
- ✅ Complete tenant isolation
- ✅ Modern tech stack (React, FastAPI, PostgreSQL)
- ✅ Docker-native deployment

**For setup instructions, see [BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md)**

**For API documentation, visit http://localhost:8000/docs after deployment**
