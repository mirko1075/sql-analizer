# 🚀 DBPower AI Cloud - Bootstrap Guide

Complete step-by-step guide to bootstrap the DBPower AI Cloud multi-tenant platform from zero to production-ready in under 5 minutes.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (30 Seconds)](#quick-start-30-seconds)
- [Detailed Bootstrap Steps](#detailed-bootstrap-steps)
- [Verification](#verification)
- [First Login & Setup](#first-login--setup)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites

### Required Software
- **Docker** 20.10+ and **Docker Compose** v2+
- **Git** for cloning the repository
- **curl** for testing APIs (optional)

### System Requirements
- **RAM**: Minimum 4GB, recommended 8GB
- **Disk Space**: At least 5GB free
- **Operating System**: Linux, macOS, or Windows with WSL2

### Available Ports
Ensure these ports are not in use:
- `3000` - Admin Panel (React frontend)
- `8080` - API Gateway
- `8001` - AI Analyzer microservice
- `8000` - Backend API
- `5440` - Internal PostgreSQL database
- `6379` - Redis cache

**Check ports availability:**
```bash
# Linux/macOS
netstat -tuln | grep -E '3000|8080|8001|8000|5440|6379'

# Windows (PowerShell)
netstat -an | findstr "3000 8080 8001 8000 5440 6379"
```

If no output, all ports are available.

---

## Quick Start (30 Seconds)

For the impatient - get everything running with 4 commands:

```bash
# 1. Clone repository
git clone https://github.com/your-org/dbpower-ai-cloud.git
cd dbpower-ai-cloud

# 2. Copy environment template
cp .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Wait for initialization (30-60 seconds)
# Watch logs: docker-compose logs -f

# Done! Open admin panel
open http://localhost:3000
```

**Default Credentials:**
- Email: `admin@dbpower.local`
- Password: `admin123`

⚠️ **Change these credentials in production!**

---

## Detailed Bootstrap Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/dbpower-ai-cloud.git
cd dbpower-ai-cloud
```

### Step 2: Configure Environment

#### Option A: Use Defaults (Development)

```bash
cp .env.example .env
```

This creates a `.env` file with development-safe defaults:
- SQLite for quick testing (or PostgreSQL for production-like)
- Demo organization enabled
- Stub AI provider (no API key needed)
- Default super admin credentials

#### Option B: Custom Configuration (Production)

Edit `.env` and customize:

```bash
cp .env.example .env
nano .env  # or vim, code, etc.
```

**Critical settings to change for production:**

```env
# Strong JWT secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-production-secret-key-change-this

# Super admin credentials
SUPER_ADMIN_EMAIL=admin@yourcompany.com
SUPER_ADMIN_PASSWORD=strong-password-here

# Disable demo organization
CREATE_DEMO_ORG=false

# Enable AI (optional)
AI_PROVIDER=openai  # or ollama for on-premise
AI_API_KEY=sk-your-openai-api-key

# Production database password
DB_PASSWORD=strong-database-password
```

### Step 3: Start Services

```bash
docker-compose up -d
```

This starts 6 services in the correct order:

1. **internal-db** - PostgreSQL database (port 5440)
2. **redis** - Cache and rate limiting (port 6379)
3. **backend** - FastAPI backend with multi-tenant API (port 8000)
4. **ai-analyzer** - AI query analysis microservice (port 8001)
5. **api-gateway** - Rate limiting, auth, routing (port 8080)
6. **admin-panel** - React admin UI with nginx (port 3000)

**First-time initialization:**
- Database schema creation: ~10 seconds
- Super admin user creation: automatic
- Service health checks: ~30 seconds

**Monitor startup:**
```bash
# Watch all logs
docker-compose logs -f

# Watch specific service
docker-compose logs -f backend
docker-compose logs -f admin-panel

# Check service status
docker-compose ps
```

**Expected output after 30-60 seconds:**
```
NAME                        STATUS              PORTS
ai-analyzer-internal-db     Up (healthy)        0.0.0.0:5440->5432/tcp
ai-analyzer-redis           Up (healthy)        0.0.0.0:6379->6379/tcp
ai-analyzer-backend         Up                  0.0.0.0:8000->8000/tcp
ai-analyzer-service         Up (healthy)        0.0.0.0:8001->8001/tcp
ai-analyzer-gateway         Up (healthy)        0.0.0.0:8080->8000/tcp
ai-analyzer-admin-panel     Up (healthy)        0.0.0.0:3000->80/tcp
```

---

## Verification

### 1. Check All Services Are Running

```bash
docker-compose ps
```

All services should show **Status: Up** (or **Up (healthy)**).

### 2. Test API Gateway Health

```bash
curl http://localhost:8080/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "timestamp": "2025-11-11T10:00:00Z"
}
```

### 3. Test Backend API

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### 4. Test AI Analyzer

```bash
curl http://localhost:8001/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "provider": "stub"
}
```

### 5. Test Admin Panel

```bash
curl http://localhost:3000/health
```

**Expected response:**
```
healthy
```

### 6. Verify Super Admin Created

Check backend logs for super admin creation:

```bash
docker-compose logs backend | grep -i "super admin"
```

**Expected output:**
```
INFO: Super admin created successfully
INFO: Email: admin@dbpower.local
INFO: API Key: org_xxxxxxxxxxxxxxxxxxxxx
```

---

## First Login & Setup

### 1. Open Admin Panel

Navigate to: **http://localhost:3000**

You should see the **DBPower AI Cloud** login page.

### 2. Login with Super Admin

Enter the default credentials:
- **Email**: `admin@dbpower.local`
- **Password**: `admin123`

Click **Sign In**.

### 3. Dashboard Overview

After successful login, you'll see the dashboard with:

**Statistics Cards:**
- Total Queries: 0 (initially)
- Total Issues: 0
- Organizations: 1 (system org) or 2 (if demo enabled)
- Avg Execution Time: 0ms

**Chart:** Query trends over time (empty initially)

### 4. Explore Features

**Left Sidebar Navigation:**

#### 📊 Dashboard
- Real-time statistics
- Query trends chart
- System health overview

#### 🏢 Organizations
- List all organizations
- View creation dates and API keys
- Create new organizations (Super Admin only)
- Manage organization settings

#### 🔍 Queries
- View all collected slow queries
- Filter: All, Analyzed, Unanalyzed
- Click query to see details
- Trigger AI analysis
- View analysis results with:
  - Severity level (Critical, High, Medium, Low)
  - Issues found
  - Optimization recommendations

### 5. Create Your First Organization

1. Click **Organizations** in sidebar
2. Click **Add Organization** button (if available)
3. Enter organization details:
   - Name: "My Company"
   - Settings: (optional JSON)
4. Save
5. Note the generated API key - needed for client agents

---

## Advanced Configuration

### JWT Secret Key (Production)

Generate a secure JWT secret:

```bash
# Linux/macOS
openssl rand -hex 32

# Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env`:
```env
JWT_SECRET_KEY=your-generated-secret-here
```

**Important**: API Gateway and Backend must use the same JWT secret!

### AI Provider Configuration

#### Option 1: OpenAI (Cloud)

```env
AI_PROVIDER=openai
AI_API_KEY=sk-your-openai-api-key-here
AI_MODEL=gpt-4
```

#### Option 2: Ollama (On-Premise)

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2
```

Add Ollama to `docker-compose.yml`:
```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama-data:/root/.ollama
```

#### Option 3: Stub (Development)

```env
AI_PROVIDER=stub
```

Uses rule-based analysis, no API key required.

### Rate Limiting Configuration

Adjust rate limits per organization:

```env
RATE_LIMIT_REQUESTS_PER_MINUTE=100  # 100 requests/min per org
RATE_LIMIT_REQUESTS_PER_HOUR=1000   # 1000 requests/hour per org
```

### Database Configuration

#### PostgreSQL (Production - Recommended)

```env
DB_TYPE=postgresql
DB_HOST=internal-db
DB_PORT=5432
DB_NAME=ai_core
DB_USER=ai_core
DB_PASSWORD=your-strong-password
```

#### SQLite (Development/Testing)

```env
DB_TYPE=sqlite
DB_PATH=./dev.db
```

### Demo Organization

Disable in production:

```env
CREATE_DEMO_ORG=false
```

Enable for testing (creates 3 demo users):
- `orgadmin@demo.com` / `demo123` (Org Admin)
- `teamlead@demo.com` / `demo123` (Team Lead)
- `user@demo.com` / `demo123` (User)

---

## Troubleshooting

### Services Won't Start

**Problem**: `docker-compose up -d` fails or services crash immediately.

**Solutions**:

1. **Check Docker is running:**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Check port conflicts:**
   ```bash
   netstat -tuln | grep -E '3000|8080|8001|8000|5440|6379'
   ```
   Kill conflicting processes or change ports in `docker-compose.yml`.

3. **Check Docker resources:**
   - Ensure Docker has at least 4GB RAM allocated
   - Ensure sufficient disk space (5GB+)

4. **View error logs:**
   ```bash
   docker-compose logs --tail=50 backend
   docker-compose logs --tail=50 internal-db
   ```

5. **Clean restart:**
   ```bash
   docker-compose down -v  # ⚠️ Deletes data!
   docker-compose up -d
   ```

### Database Initialization Fails

**Problem**: Backend logs show database connection errors or schema errors.

**Solutions**:

1. **Check database is healthy:**
   ```bash
   docker-compose ps internal-db
   docker-compose logs internal-db
   ```

2. **Verify database credentials:**
   Check `.env` matches `docker-compose.yml` settings.

3. **Manual database initialization:**
   ```bash
   docker-compose exec backend python -m backend.db.init_database
   ```

4. **Reset database:**
   ```bash
   docker-compose down -v
   docker volume rm dbpower-ai-cloud_postgres-data
   docker-compose up -d internal-db
   # Wait 10 seconds
   docker-compose up -d backend
   ```

### Admin Panel Not Loading

**Problem**: http://localhost:3000 shows "Connection refused" or blank page.

**Solutions**:

1. **Check admin-panel service:**
   ```bash
   docker-compose ps admin-panel
   docker-compose logs admin-panel
   ```

2. **Check API Gateway is running:**
   ```bash
   curl http://localhost:8080/health
   ```

3. **Check browser console (F12):**
   - CORS errors → Check API Gateway CORS configuration
   - Network errors → Check API Gateway is accessible
   - Authentication errors → Check JWT secret matches

4. **Rebuild admin panel:**
   ```bash
   docker-compose build admin-panel
   docker-compose up -d admin-panel
   ```

### Cannot Login - Invalid Credentials

**Problem**: Login with default credentials fails with "Invalid email or password".

**Solutions**:

1. **Check super admin was created:**
   ```bash
   docker-compose logs backend | grep "Super admin"
   ```

2. **Verify credentials in `.env`:**
   ```bash
   cat .env | grep SUPER_ADMIN
   ```

3. **Manually create super admin:**
   ```bash
   docker-compose exec backend python -c "
   from backend.db.init_database import create_super_admin
   create_super_admin('admin@test.com', 'password123', 'Admin User')
   "
   ```

4. **Reset database and recreate:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

### API Gateway Returns 502 Bad Gateway

**Problem**: Admin panel shows "502 Bad Gateway" errors.

**Solutions**:

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check API Gateway configuration:**
   ```bash
   docker-compose logs api-gateway | grep ERROR
   ```

3. **Verify backend URL in API Gateway:**
   Check `docker-compose.yml`:
   ```yaml
   api-gateway:
     environment:
       BACKEND_URL: http://backend:8000  # Must be service name!
   ```

4. **Restart services:**
   ```bash
   docker-compose restart api-gateway backend
   ```

### AI Analysis Not Working

**Problem**: "Analyze" button does nothing or shows errors.

**Solutions**:

1. **Check AI Analyzer is running:**
   ```bash
   curl http://localhost:8001/health
   ```

2. **Check provider configuration:**
   ```bash
   docker-compose logs ai-analyzer
   ```

3. **If using OpenAI, verify API key:**
   ```bash
   cat .env | grep AI_API_KEY
   ```

4. **Test analysis manually:**
   ```bash
   curl -X POST http://localhost:8001/analyzer/analyze \
     -H "Content-Type: application/json" \
     -d '{"slow_query_id": 1}'
   ```

---

## Next Steps

### 1. Deploy Client Agents

Install client agents on your database servers to collect slow queries:

```bash
cd client-agent
pip install -r requirements.txt

# Configure
export ORG_API_KEY="your-org-api-key"
export BACKEND_URL="http://your-server:8080"

# Run collector
python collector.py --database mysql --host localhost --port 3306
```

See [client-agent/README.md](client-agent/README.md) for details.

### 2. Configure Organizations & Teams

1. Create organizations for each tenant
2. Create teams within organizations
3. Create identities for fine-grained access
4. Invite users with appropriate roles

### 3. Set Up Monitoring

Monitor service health:

```bash
# All services
watch -n 5 'docker-compose ps'

# API Gateway metrics
curl http://localhost:8080/metrics  # if enabled

# Backend logs
docker-compose logs -f backend | grep ERROR
```

### 4. Configure Alerts (Optional)

Set up alerts for:
- High query counts
- Critical severity issues
- Service downtime
- Rate limit exceeded

### 5. Backup Strategy

Set up automated backups:

```bash
# Backup database
docker-compose exec -T internal-db pg_dump -U ai_core ai_core > backup_$(date +%Y%m%d).sql

# Backup Redis (optional)
docker-compose exec -T redis redis-cli SAVE
```

### 6. Read Additional Documentation

- [README.md](README.md) - Project overview and architecture
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture diagrams
- [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md) - Environment configuration
- [admin-panel/README.md](admin-panel/README.md) - Admin panel documentation
- [api-gateway/README.md](api-gateway/README.md) - API Gateway documentation
- [Phase PRs](https://github.com/your-org/dbpower-ai-cloud/pulls) - Implementation details for each phase

---

## Production Deployment Checklist

Before going to production:

- [ ] Change all default passwords
- [ ] Generate new JWT secret (32+ characters)
- [ ] Use PostgreSQL (not SQLite)
- [ ] Disable demo organization
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules (close ports 5440, 6379, 8000, 8001)
- [ ] Only expose API Gateway (8080) and Admin Panel (3000)
- [ ] Configure backup schedule
- [ ] Set up monitoring and alerting
- [ ] Review rate limits
- [ ] Test disaster recovery
- [ ] Enable audit logging
- [ ] Review RBAC permissions
- [ ] Load test the system
- [ ] Document runbooks for ops team

---

## Support

- 📖 **Documentation**: See [README.md](README.md) and linked guides
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/dbpower-ai-cloud/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-org/dbpower-ai-cloud/discussions)
- 📧 **Email**: support@yourcompany.com

---

## Summary

**You've successfully bootstrapped DBPower AI Cloud!** 🎉

Your multi-tenant database query analysis platform is now running with:
- ✅ 6 services orchestrated with Docker Compose
- ✅ Multi-tenant database with organization hierarchy
- ✅ JWT authentication and RBAC
- ✅ API Gateway with rate limiting
- ✅ AI-powered query analysis
- ✅ Modern React admin panel
- ✅ Super admin user created

**Next**: Deploy client agents to your databases and start collecting queries!

**Questions?** Check the [Troubleshooting](#troubleshooting) section or open an issue.

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-11
**Platform Version**: Phase 1-6 Complete
