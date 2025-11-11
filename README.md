# DBPower AI Cloud

**Enterprise Multi-Tenant Platform for Database Query Analysis and Optimization**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)

---

## 🎯 Overview

DBPower AI Cloud is a complete **multi-tenant SaaS platform** for collecting, analyzing, and optimizing slow database queries across MySQL and PostgreSQL databases. Built with enterprise-grade security, role-based access control, and AI-powered analysis, it helps database administrators and developers identify performance bottlenecks and improve query efficiency.

### Key Features

🏢 **Multi-Tenancy**
- Organization → Team → Identity → User hierarchy
- Complete tenant isolation with automatic query filtering
- Per-organization rate limiting and API keys
- Audit logging for compliance

🔐 **Enterprise Security**
- JWT-based authentication with refresh tokens
- Role-Based Access Control (RBAC): Super Admin, Org Admin, Team Lead, User
- API key authentication for client agents
- Request signing for replay attack protection
- PII anonymization in collected queries

🤖 **AI-Powered Analysis**
- Multi-provider support: OpenAI (cloud) and Ollama (on-premise)
- Automatic severity classification (Critical, High, Medium, Low)
- Issue detection and optimization recommendations
- Query pattern recognition

🚀 **Modern Architecture**
- Microservices with Docker Compose orchestration
- API Gateway with rate limiting and request routing
- Redis-backed distributed caching
- React 18 admin panel with real-time updates

📊 **Comprehensive Management**
- Web-based admin panel for multi-tenant management
- Real-time statistics and query trend visualization
- Organization, team, and user management
- Client agent deployment for on-premise databases

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DBPower AI Cloud Platform                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐        ┌──────────────────┐                   │
│  │  Admin Panel     │───────▶│  API Gateway     │                   │
│  │  React + Nginx   │        │  Rate Limiting   │                   │
│  │  Port 3000       │        │  Auth Middleware │                   │
│  └──────────────────┘        │  Port 8080       │                   │
│                               └────────┬─────────┘                   │
│                                        │                              │
│                          ┌─────────────┴───────────────┐             │
│                          │                             │             │
│                          ▼                             ▼             │
│                ┌──────────────────┐         ┌──────────────────┐    │
│                │  Backend API     │         │  AI Analyzer     │    │
│                │  FastAPI         │◀────────│  OpenAI/Ollama   │    │
│                │  Multi-Tenant    │         │  Port 8001       │    │
│                │  Port 8000       │         └──────────────────┘    │
│                └────────┬─────────┘                                  │
│                         │                                             │
│              ┌──────────┼──────────┐                                 │
│              │          │          │                                 │
│              ▼          ▼          ▼                                 │
│      ┌──────────┐  ┌────────┐  ┌────────────┐                      │
│      │   Redis  │  │ PG DB  │  │  Audit     │                      │
│      │  Cache   │  │ Multi- │  │  Logging   │                      │
│      │  6379    │  │ Tenant │  │            │                      │
│      └──────────┘  │  5440  │  └────────────┘                      │
│                     └────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │   Client Agents (On-Premise)  │
              │   ┌──────────┐  ┌──────────┐ │
              │   │  MySQL   │  │ Postgres │ │
              │   │ Collector│  │Collector │ │
              │   └──────────┘  └──────────┘ │
              └───────────────────────────────┘
```

---

## 🚀 Quick Start

Get DBPower AI Cloud running in under 2 minutes:

### Prerequisites

- Docker 20.10+ and Docker Compose v2+
- 4GB RAM minimum (8GB recommended)
- Ports available: 3000, 8080, 8001, 8000, 5440, 6379

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-org/dbpower-ai-cloud.git
cd dbpower-ai-cloud

# 2. Copy environment template
cp .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Wait for initialization (30-60 seconds)
docker-compose logs -f

# 5. Access admin panel
open http://localhost:3000
```

### Default Credentials

- **Email**: `admin@dbpower.local`
- **Password**: `admin123`

⚠️ **Change these immediately in production!**

### Verify Installation

```bash
# Check all services are healthy
docker-compose ps

# Test API Gateway
curl http://localhost:8080/health

# Test Backend
curl http://localhost:8000/health

# Test AI Analyzer
curl http://localhost:8001/health
```

**For detailed setup instructions, see [BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md)**

---

## 📦 Components

DBPower AI Cloud is built in 6 phases, each adding critical functionality:

### Phase 1-2: Multi-Tenant Backend + Authentication

**Technology**: Python, FastAPI, PostgreSQL, SQLAlchemy, JWT

**Features**:
- Multi-tenant database schema (Organization → Team → Identity → User)
- SQLAlchemy ORM models with proper relationships
- JWT authentication with access and refresh tokens
- API key authentication for client agents
- Password hashing with bcrypt
- RBAC with 4 roles: Super Admin, Org Admin, Team Lead, User
- Tenant isolation middleware
- Audit logging for compliance

**API Endpoints**:
- `/api/v1/auth/*` - Authentication and authorization
- `/api/v1/admin/*` - CRUD for organizations, teams, identities, users
- `/api/v1/slow-queries/*` - Query collection and retrieval
- `/api/v1/stats/*` - Statistics and analytics

**Branch**: `feature/phase-1-2-multitenant`

### Phase 3: Client Agent

**Technology**: Python, asyncio, cryptography

**Features**:
- On-premise database connectors (MySQL, PostgreSQL)
- Automatic slow query collection
- PII anonymization with 3 levels (strict, moderate, minimal)
- Pattern detection (emails, IPs, credit cards, SSNs, phone numbers)
- Secure HTTP client with retry logic
- Request signing for replay attack protection
- Configurable collection intervals

**Usage**:
```bash
cd client-agent
pip install -r requirements.txt
export ORG_API_KEY="your-org-api-key"
export BACKEND_URL="http://your-server:8080"
python collector.py --database mysql --host localhost --port 3306
```

**Branch**: `feature/phase-3-client-agent`

### Phase 4: AI Analyzer Microservice

**Technology**: Python, FastAPI, OpenAI, Ollama

**Features**:
- Multi-provider AI support (OpenAI cloud, Ollama on-premise)
- Query analysis with severity classification
- Issue detection and optimization recommendations
- Stub provider for testing (no API key required)
- RESTful API with Pydantic validation
- Docker deployment with health checks

**API Endpoints**:
- `POST /analyzer/analyze` - Analyze a slow query
- `GET /health` - Health check

**Branch**: `feature/phase-4-ai-analyzer`

### Phase 5: API Gateway

**Technology**: Python, FastAPI, Redis

**Features**:
- Centralized routing for all services
- JWT authentication middleware
- Redis-backed distributed rate limiting
- Token bucket algorithm for rate limiting
- Per-organization and per-IP limits
- Request/response logging
- CORS middleware
- HTTP request proxying with error handling

**Configuration**:
- Rate limits: 100 req/min, 1000 req/hour per organization
- Configurable via environment variables

**Branch**: `feature/phase-5-api-gateway`

### Phase 6: Admin Panel

**Technology**: React 18, TypeScript, Vite, Nginx

**Features**:
- Modern React SPA with TypeScript
- JWT authentication with protected routes
- Dashboard with real-time statistics
- Organization, team, and user management
- Advanced query analysis interface with filtering
- AI analysis trigger with live status
- Responsive design with Lucide icons
- Recharts for data visualization
- React Query for server state management
- Zustand for client state management

**Pages**:
- Login - Authentication
- Dashboard - Statistics and trends
- Organizations - Multi-tenant management
- Queries - Query analysis with AI results

**Branch**: `feature/phase-6-admin-panel`

---

## 📋 Service Endpoints

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Admin Panel** | 3000 | http://localhost:3000 | Web UI for management |
| **API Gateway** | 8080 | http://localhost:8080 | Entry point for all API requests |
| **Backend API** | 8000 | http://localhost:8000 | Core business logic and data |
| **AI Analyzer** | 8001 | http://localhost:8001 | AI-powered query analysis |
| **PostgreSQL** | 5440 | localhost:5440 | Multi-tenant database |
| **Redis** | 6379 | localhost:6379 | Cache and rate limiting |

---

## 🔧 Configuration

### Environment Variables

The `.env` file controls all configuration. Key settings:

```env
# Database
DB_TYPE=postgresql
DB_HOST=internal-db
DB_PASSWORD=change-in-production

# Authentication
JWT_SECRET_KEY=generate-secure-key-here
SUPER_ADMIN_EMAIL=admin@yourcompany.com
SUPER_ADMIN_PASSWORD=strong-password

# AI Provider
AI_PROVIDER=openai  # or ollama or stub
AI_API_KEY=sk-your-openai-api-key

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_REQUESTS_PER_HOUR=1000

# Demo (disable in production)
CREATE_DEMO_ORG=false
```

**For complete configuration options, see [.env.example](.env.example)**

### Generate JWT Secret

```bash
# Option 1: OpenSSL
openssl rand -hex 32

# Option 2: Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📚 Documentation

- **[🚀 BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md)** - Complete setup guide (START HERE!)
- **[🏗️ ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture and data flow
- **[⚙️ ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md)** - Environment configuration
- **[📱 admin-panel/README.md](admin-panel/README.md)** - Admin panel documentation
- **[🌐 api-gateway/README.md](api-gateway/README.md)** - API Gateway documentation
- **[🤖 ai-analyzer/README.md](ai-analyzer/README.md)** - AI Analyzer documentation
- **[🔌 client-agent/README.md](client-agent/README.md)** - Client Agent documentation

---

## 🔒 Security

### Authentication & Authorization

- **JWT Tokens**: Access tokens (30 min) + refresh tokens (7 days)
- **API Keys**: Per-organization keys for client agents
- **Password Hashing**: bcrypt with salt
- **Request Signing**: HMAC-SHA256 signatures for replay protection

### Multi-Tenancy & Isolation

- **Tenant Middleware**: Automatic query filtering by organization
- **Row-Level Security**: Database constraints prevent cross-tenant data access
- **API Key Scoping**: Each org's API key only accesses their data

### Data Protection

- **PII Anonymization**: Automatic masking of emails, IPs, credit cards, SSNs
- **Audit Logging**: All actions logged with user/org/resource tracking
- **Rate Limiting**: Prevents abuse and DoS attacks

### Production Checklist

- [ ] Change all default passwords
- [ ] Generate new JWT secret (32+ chars)
- [ ] Use strong database passwords
- [ ] Disable demo organization
- [ ] Configure HTTPS/SSL
- [ ] Set up firewall (close internal ports)
- [ ] Enable audit logging
- [ ] Configure backups
- [ ] Set up monitoring

**For security best practices, see [SECURITY.md](SECURITY.md)**

---

## 🛠️ Development

### Project Structure

```
dbpower-ai-cloud/
├── admin-panel/              # React frontend (Phase 6)
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Route pages
│   │   ├── services/         # API client
│   │   ├── store/            # State management
│   │   └── types/            # TypeScript definitions
│   ├── Dockerfile
│   └── nginx.conf
├── api-gateway/              # API Gateway (Phase 5)
│   ├── core/
│   │   ├── rate_limiter.py   # Redis-backed rate limiting
│   │   └── proxy.py          # HTTP proxying
│   ├── middleware/           # Auth, rate limit, logging
│   ├── gateway.py            # Main FastAPI app
│   └── Dockerfile
├── ai-analyzer/              # AI Analysis (Phase 4)
│   ├── providers/
│   │   ├── openai_provider.py
│   │   ├── ollama_provider.py
│   │   └── stub_provider.py
│   ├── analyzer.py           # Main FastAPI app
│   └── Dockerfile
├── backend/                  # Core backend (Phase 1-2)
│   ├── api/
│   │   └── routes/           # API endpoints
│   ├── db/
│   │   ├── models_multitenant.py  # SQLAlchemy models
│   │   └── init_database.py       # DB initialization
│   ├── middleware/           # Auth, tenant isolation, audit
│   ├── services/             # Business logic
│   ├── main.py               # FastAPI app
│   └── Dockerfile
├── client-agent/             # On-premise collector (Phase 3)
│   ├── anonymizer/           # PII anonymization
│   ├── collectors/           # MySQL, PostgreSQL collectors
│   ├── collector.py          # Main script
│   └── requirements.txt
├── docker-compose.yml        # Full stack orchestration
├── .env.example              # Environment template
├── README.md                 # This file
├── BOOTSTRAP_GUIDE.md        # Setup guide
└── ARCHITECTURE.md           # Architecture docs
```

### Running Locally

**Backend Development**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Admin Panel Development**:
```bash
cd admin-panel
npm install
npm run dev  # Runs on port 3000 with Vite HMR
```

**API Gateway Development**:
```bash
cd api-gateway
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn gateway:app --reload --port 8080
```

---

## 🧪 Testing

### Health Checks

```bash
# All services
curl http://localhost:8080/health  # API Gateway
curl http://localhost:8000/health  # Backend
curl http://localhost:8001/health  # AI Analyzer
curl http://localhost:3000/health  # Admin Panel
```

### API Testing

```bash
# Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@dbpower.local","password":"admin123"}'

# Get organizations (with token)
curl http://localhost:8080/api/v1/admin/organizations \
  -H "Authorization: Bearer YOUR_TOKEN"

# List slow queries
curl http://localhost:8080/api/v1/slow-queries

# Trigger analysis
curl -X POST http://localhost:8080/analyzer/analyze \
  -H "Content-Type: application/json" \
  -d '{"slow_query_id": 1}'
```

### Unit Tests

```bash
# Backend tests (Phase 1-2)
cd backend
pytest tests/

# Client agent tests (Phase 3)
cd client-agent
pytest tests/
```

---

## 🚢 Deployment

### Docker Compose (Recommended)

```bash
# Development
docker-compose up -d

# Production (with .env.prod)
docker-compose -f docker-compose.yml --env-file .env.prod up -d
```

### Individual Services

```bash
# Build images
docker-compose build

# Start specific service
docker-compose up -d admin-panel

# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart api-gateway

# Stop all
docker-compose down

# Clean restart (removes data!)
docker-compose down -v
docker-compose up -d
```

### Scaling

```bash
# Scale backend to 4 instances
docker-compose up -d --scale backend=4

# Scale with custom workers
docker-compose up -d backend --scale backend=4 -e BACKEND_WORKERS=2
```

---

## 📊 Monitoring

### Service Health

```bash
# Check all services
docker-compose ps

# Detailed health
docker-compose ps | grep "healthy"

# Service-specific logs
docker-compose logs --tail=100 -f backend
```

### Database

```bash
# Connect to PostgreSQL
docker-compose exec internal-db psql -U ai_core ai_core

# View organizations
SELECT id, name, created_at FROM organizations;

# View users
SELECT id, email, role, is_active FROM users;
```

### Redis

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View keys
KEYS *

# Check rate limit
GET rate_limit:org:1
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest` and `npm test`
5. Commit: `git commit -m 'feat: add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use type hints, run `black` and `ruff`
- **TypeScript**: Follow ESLint rules, use strict mode
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - UI library
- **PostgreSQL** - Robust relational database
- **Redis** - High-performance caching
- **Docker** - Containerization platform
- **OpenAI** - AI-powered analysis
- **Ollama** - Local AI models

---

## 📞 Support

- **Documentation**: See guides in this repository
- **Issues**: [GitHub Issues](https://github.com/your-org/dbpower-ai-cloud/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/dbpower-ai-cloud/discussions)
- **Email**: support@yourcompany.com

---

## 🗺️ Roadmap

### Completed (Phase 1-6)
- ✅ Multi-tenant architecture
- ✅ JWT authentication and RBAC
- ✅ Client agents with PII anonymization
- ✅ AI-powered query analysis
- ✅ API Gateway with rate limiting
- ✅ React admin panel

### Upcoming
- [ ] Team and user management UI
- [ ] Identity (client agent) management
- [ ] Real-time query updates via WebSocket
- [ ] Advanced analytics and dashboards
- [ ] Query execution simulation
- [ ] Automated index recommendations
- [ ] Email/Slack notifications
- [ ] Grafana integration
- [ ] Multi-language support (i18n)
- [ ] Mobile app
- [ ] Kubernetes deployment
- [ ] Terraform infrastructure

---

**Built with ❤️ for database performance optimization**

**Get Started**: [BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md) | **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
