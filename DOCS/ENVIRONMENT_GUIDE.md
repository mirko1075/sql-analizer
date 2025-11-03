# 🚀 AI Query Analyzer - Environment Setup Guide

Complete guide to setting up and running the AI Query Analyzer environment.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Service Endpoints](#service-endpoints)

---

## Prerequisites

### Required Software
- **Docker** and **Docker Compose** (v2+)
- **Python 3.12+** (for test scripts)
- **Node.js 18+** (for frontend, if running locally)
- **Git**

### System Requirements
- **RAM**: Minimum 8GB, recommended 16GB
- **Disk Space**: At least 10GB free
- **Ports**: The following ports must be available:
  - `3307` - MySQL Lab
  - `5433` - PostgreSQL Lab
  - `5440` - Internal PostgreSQL
  - `6379` - Redis
  - `8000` - Backend API
  - `5173` - Frontend

---

## Quick Start

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd sql-analizer
```

### 2. Start Everything
```bash
# Start main application
./start.sh

# In a separate terminal, start lab databases
cd ai-query-lab
docker compose up -d
```

### 3. Verify
```bash
# Check all services are running
docker ps

# Check backend health
curl http://localhost:8000/health

# Open frontend in browser
open http://localhost:5173
```

**You're ready!** Skip to [Running Tests](TESTING_GUIDE.md) to start testing.

---

## Detailed Setup

### Step 1: Start Main Application Services

The main application consists of 4 services:
- **internal-db**: PostgreSQL database for storing analysis results
- **redis**: Cache and queue system
- **backend**: FastAPI backend API
- **frontend**: React frontend UI

```bash
cd /path/to/sql-analizer

# Start all services
docker compose up -d

# Or use the helper script
./start.sh
```

**Wait 30 seconds** for services to initialize.

### Step 2: Start Lab Databases

Lab databases are separate containers that simulate production databases for testing:

```bash
cd ai-query-lab

# Start MySQL and PostgreSQL lab databases
docker compose up -d

# Verify they're running
docker ps | grep -E "mysql-lab|postgres-lab"
```

Lab databases will automatically:
- Create test tables (`users`, `orders`)
- Populate with sample data (MySQL: 200k users, 500k orders | PostgreSQL: 50k users, 150k orders)
- Enable slow query logging
- Configure performance monitoring

### Step 3: Install Python Dependencies (for running tests)

```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install mysql-connector-python psycopg2-binary python-dotenv
```

### Step 4: Verify Installation

Run the verification script:

```bash
./validate.sh
```

This checks:
- ✅ All Docker containers are running
- ✅ Databases are accessible
- ✅ Backend API is responding
- ✅ Frontend is serving
- ✅ Lab databases have data

---

## Verification

### Check Service Status

```bash
# All services
docker ps

# Main application services
docker compose ps

# Lab database services
cd ai-query-lab && docker compose ps
```

### Test Database Connections

**MySQL Lab:**
```bash
docker exec -it mysql-lab mysql -uroot -proot -e "USE labdb; SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM orders;"
```

Expected output:
```
COUNT(*)
200000

COUNT(*)
500000
```

**PostgreSQL Lab:**
```bash
docker exec -it postgres-lab psql -U postgres -d labdb -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM orders;"
```

Expected output:
```
 count
-------
 50000

 count
--------
 150000
```

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health | jq

# List slow queries
curl http://localhost:8000/api/v1/slow-queries | jq
```

### Test Frontend

Open browser: http://localhost:5173

You should see the AI Query Analyzer dashboard.

---

## Service Endpoints

### Main Application

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Frontend** | 5173 | http://localhost:5173 | Web UI |
| **Backend API** | 8000 | http://localhost:8000 | REST API |
| **API Docs** | 8000 | http://localhost:8000/docs | Interactive API documentation |
| **Internal DB** | 5440 | localhost:5440 | PostgreSQL (analysis data) |
| **Redis** | 6379 | localhost:6379 | Cache/Queue |

### Lab Databases

| Service | Port | Credentials | Purpose |
|---------|------|-------------|---------|
| **MySQL Lab** | 3307 | root/root | Test database for MySQL slow queries |
| **PostgreSQL Lab** | 5433 | postgres/root | Test database for PostgreSQL slow queries |

### API Endpoints

Key API endpoints:

```bash
# Health check
GET /health

# Slow queries
GET /api/v1/slow-queries
GET /api/v1/slow-queries/{id}

# Statistics
GET /api/v1/stats/global
GET /api/v1/stats/database/{db_type}

# Collectors (manual trigger)
POST /api/v1/collectors/mysql/collect
POST /api/v1/collectors/postgres/collect

# Analyzer (manual trigger)
POST /api/v1/analyzer/analyze
```

---

## Troubleshooting

### Services Won't Start

**Problem**: Docker containers fail to start

**Solutions**:
```bash
# Check if ports are already in use
netstat -tuln | grep -E '3307|5433|5440|6379|8000|5173'

# Stop existing services
docker compose down
cd ai-query-lab && docker compose down

# Remove volumes and restart (⚠️ deletes data)
docker compose down -v
docker compose up -d
```

### Database Connection Errors

**Problem**: Backend can't connect to internal database

**Solution**:
```bash
# Check database is healthy
docker logs ai-analyzer-internal-db

# Restart database
docker compose restart internal-db

# Wait 10 seconds and check again
sleep 10 && curl http://localhost:8000/health
```

### No Slow Queries Collected

**Problem**: Slow queries not appearing in frontend

**Possible causes**:
1. Lab databases not running
2. No queries executed yet
3. Collector hasn't run yet (runs every 5 minutes)

**Solutions**:
```bash
# 1. Verify lab databases are running
docker ps | grep -E "mysql-lab|postgres-lab"

# 2. Manually run a slow query
docker exec -it mysql-lab mysql -uroot -proot labdb -e "SELECT * FROM orders WHERE product LIKE '%phone%'"

# 3. Force collector to run immediately
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect
curl -X POST http://localhost:8000/api/v1/collectors/postgres/collect

# 4. Force analysis
curl -X POST http://localhost:8000/api/v1/analyzer/analyze

# 5. Check results
curl http://localhost:8000/api/v1/slow-queries | jq
```

### Frontend Shows Empty Dashboard

**Problem**: Frontend loads but shows no data

**Solution**:
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check browser console for errors (F12)

# Verify CORS settings - should allow localhost:5173
docker logs ai-analyzer-backend | grep CORS
```

### Python Dependencies Missing

**Problem**: Test scripts fail with import errors

**Solution**:
```bash
pip install mysql-connector-python psycopg2-binary python-dotenv
```

### Permission Denied Errors

**Problem**: Can't access Docker commands

**Solution**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo
sudo docker compose up -d
```

---

## Stopping Services

### Stop All Services
```bash
# Stop main application
docker compose down

# Stop lab databases
cd ai-query-lab && docker compose down
```

### Stop and Remove Data
```bash
# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v
cd ai-query-lab && docker compose down -v
```

### Stop Individual Services
```bash
# Stop only backend
docker stop ai-analyzer-backend

# Stop only one lab database
docker stop mysql-lab
```

---

## Next Steps

Once your environment is running:
1. 📖 Read the [Testing Guide](TESTING_GUIDE.md) to learn how to run performance tests
2. 🧪 Run your first tests with `cd ai-query-lab/tests && ./run_tests.sh mysql`
3. 🔍 Explore the frontend at http://localhost:5173
4. 📊 Check the [Test README](ai-query-lab/tests/README_TESTS.md) for test documentation

---

## Advanced Configuration

### Environment Variables

Main application env vars (in `.env` or `docker-compose.yml`):

```bash
# Internal database
INTERNAL_DB_HOST=internal-db
INTERNAL_DB_PORT=5432
INTERNAL_DB_USER=ai_core
INTERNAL_DB_PASSWORD=ai_core
INTERNAL_DB_NAME=ai_core

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Lab databases (for collectors)
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=labdb

PG_HOST=host.docker.internal
PG_PORT=5433
PG_USER=postgres
PG_PASSWORD=root
PG_DB=labdb

# Collector settings
COLLECTOR_INTERVAL=300  # seconds (5 minutes)
ANALYZER_INTERVAL=600   # seconds (10 minutes)

# Logging
LOG_LEVEL=INFO
ENV=development
```

### Custom Ports

To use different ports, edit `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Change 8080 to your desired port
```

### Development Mode

For development with hot-reload:

```bash
# Backend - Python auto-reload is enabled by default in docker-compose
docker compose logs -f backend

# Frontend - Vite dev server with HMR
cd frontend
npm install
npm run dev
```

---

## Support

- 🐛 Report issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📚 Documentation: See [README.md](README.md) and [TESTING_GUIDE.md](TESTING_GUIDE.md)
- 💬 Questions: Check existing issues or create a new one

---

**Ready to test?** Continue to [TESTING_GUIDE.md](TESTING_GUIDE.md)
