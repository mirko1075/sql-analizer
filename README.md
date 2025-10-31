# AI Query Analyzer

Enterprise-grade slow query analysis platform that automatically collects, analyzes, and provides optimization recommendations for MySQL and PostgreSQL databases.

## Overview

AI Query Analyzer is a comprehensive solution for identifying and optimizing slow database queries. It combines automated query collection, rule-based analysis, and AI-ready infrastructure to help database administrators and developers improve query performance.

### Key Features

- **Automatic Query Collection**: Monitors MySQL and PostgreSQL databases for slow queries
- **Intelligent Analysis**: Rule-based query analysis with AI integration capability
- **Modern Dashboard**: React-based UI with real-time statistics and insights
- **Production Ready**: Docker-based deployment with health checks and monitoring
- **Multi-Database Support**: Works with both MySQL and PostgreSQL
- **Query Fingerprinting**: Normalizes queries to identify patterns
- **EXPLAIN Plan Analysis**: Automatic execution plan analysis for optimization hints

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Query Analyzer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │   Frontend   │───▶│   Backend    │───▶│  Internal DB    │   │
│  │  React + TS  │    │   FastAPI    │    │  PostgreSQL 15  │   │
│  │  (Port 3000) │    │  (Port 8000) │    │   (Port 5440)   │   │
│  └──────────────┘    └──────┬───────┘    └─────────────────┘   │
│                              │                                    │
│                              │            ┌─────────────────┐   │
│                              └───────────▶│     Redis       │   │
│                                            │  Cache + Queue  │   │
│                                            └─────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Scheduler (APScheduler)                      │  │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │  │
│  │  │ MySQL Collector │    │ PostgreSQL Collector    │     │  │
│  │  │  (Every 5 min)  │    │     (Every 5 min)       │     │  │
│  │  └────────┬────────┘    └──────────┬──────────────┘     │  │
│  │           │                         │                     │  │
│  │           └──────────┬──────────────┘                     │  │
│  │                      ▼                                     │  │
│  │           ┌─────────────────────┐                         │  │
│  │           │   Query Analyzer    │                         │  │
│  │           │   (Every 10 min)    │                         │  │
│  │           └─────────────────────┘                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │         External Lab Databases             │
        │  ┌──────────────┐    ┌─────────────────┐  │
        │  │ MySQL Lab    │    │ PostgreSQL Lab  │  │
        │  │ (Port 3307)  │    │   (Port 5433)   │  │
        │  └──────────────┘    └─────────────────┘  │
        └───────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Start in Development Mode

```bash
# Clone the repository
git clone <repository-url>
cd sql-analizer

# Make startup script executable
chmod +x start.sh

# Start all services (lab databases + application)
./start.sh dev
```

After ~30 seconds, access:
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MySQL Lab**: `localhost:3307` (user: root, password: root)
- **PostgreSQL Lab**: `localhost:5433` (user: postgres, password: postgres)

### Start in Production Mode

```bash
# Copy and configure production environment
cp .env.prod.example .env.prod
nano .env.prod  # Edit with your production values

# Start in production mode
./start.sh prod
```

Production access:
- **Frontend**: [http://localhost:80](http://localhost:80)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

### Other Commands

```bash
# Start only lab databases
./start.sh lab

# Stop all services
./start.sh stop

# Clean up everything (removes data!)
./start.sh clean

# View logs
./start.sh logs
```

## Installation

### Manual Installation (Development)

#### 1. Start Lab Databases

```bash
cd ai-query-lab
docker compose up -d
cd ..
```

#### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export INTERNAL_DB_HOST=localhost
export INTERNAL_DB_PORT=5440
export INTERNAL_DB_USER=ai_core
export INTERNAL_DB_PASSWORD=ai_core_pass
export INTERNAL_DB_NAME=ai_core

export REDIS_HOST=localhost
export REDIS_PORT=6379

export MYSQL_HOST=localhost
export MYSQL_PORT=3307
export MYSQL_USER=root
export MYSQL_PASSWORD=root

export PG_HOST=localhost
export PG_PORT=5433
export PG_USER=postgres
export PG_PASSWORD=postgres

# Run backend
uvicorn backend.main:app --reload
```

#### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Installation (Recommended)

Use the provided [start.sh](start.sh) script for automated Docker deployment.

## Configuration

### Environment Variables

#### Backend Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `INTERNAL_DB_HOST` | Internal PostgreSQL host | `internal-db` |
| `INTERNAL_DB_PORT` | Internal PostgreSQL port | `5432` |
| `INTERNAL_DB_USER` | Internal database user | `ai_core` |
| `INTERNAL_DB_PASSWORD` | Internal database password | `ai_core_pass` |
| `INTERNAL_DB_NAME` | Internal database name | `ai_core` |
| `REDIS_HOST` | Redis host | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | (none) |
| `MYSQL_HOST` | MySQL lab host | `localhost` |
| `MYSQL_PORT` | MySQL lab port | `3307` |
| `MYSQL_USER` | MySQL lab user | `root` |
| `MYSQL_PASSWORD` | MySQL lab password | `root` |
| `PG_HOST` | PostgreSQL lab host | `localhost` |
| `PG_PORT` | PostgreSQL lab port | `5433` |
| `PG_USER` | PostgreSQL lab user | `postgres` |
| `PG_PASSWORD` | PostgreSQL lab password | `postgres` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENV` | Environment | `development` |

#### Frontend Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

### Collector Configuration

Collectors can be configured via the API or [backend/services/scheduler.py](backend/services/scheduler.py):

```python
# Collection interval (minutes)
scheduler.start(interval_minutes=5)

# Minimum duration threshold (ms)
collector.fetch_slow_queries(min_duration_ms=1000.0, limit=100)
```

### Analyzer Configuration

Analyzer thresholds in [backend/services/analyzer.py](backend/services/analyzer.py):

```python
# Duration threshold for heuristic analysis
DURATION_THRESHOLD_MS = 5000

# Rows examined/returned ratio threshold
ROW_RATIO_THRESHOLD = 100
```

## Database Schema

### Internal Database Tables

1. **slow_query_raw** - Raw collected queries
2. **slow_query_fingerprint** - Normalized query patterns
3. **analysis_result** - Analysis results and suggestions
4. **collector_run_history** - Collection execution logs
5. **feedback_history** - User feedback for learning loop

### Views

- **v_slow_query_summary** - Aggregated query statistics
- **v_improvement_opportunities** - Queries with optimization potential

See [backend/db/init_schema.sql](backend/db/init_schema.sql) for complete schema.

## API Documentation

### Endpoints

#### Slow Queries

- `GET /api/v1/slow-queries` - List slow queries (paginated)
- `GET /api/v1/slow-queries/{id}` - Get query details
- `GET /api/v1/slow-queries/{id}/raw` - Get raw query instances
- `GET /api/v1/slow-queries/{id}/analysis` - Get analysis results

#### Statistics

- `GET /api/v1/stats` - Get system statistics
- `GET /api/v1/stats/by-database` - Database distribution
- `GET /api/v1/stats/by-improvement` - Improvement distribution

#### Collectors

- `POST /api/v1/collectors/mysql/collect` - Trigger MySQL collection
- `POST /api/v1/collectors/postgres/collect` - Trigger PostgreSQL collection
- `GET /api/v1/collectors/status` - Get collector status
- `POST /api/v1/collectors/start` - Start scheduler
- `POST /api/v1/collectors/stop` - Stop scheduler

#### Analyzer

- `POST /api/v1/analyzer/analyze` - Trigger analysis
- `POST /api/v1/analyzer/analyze/{id}` - Analyze specific query
- `GET /api/v1/analyzer/status` - Get analyzer status

#### Health

- `GET /health` - Health check endpoint

Full API documentation available at [http://localhost:8000/docs](http://localhost:8000/docs) when running.

## Development

### Project Structure

```
sql-analizer/
├── ai-query-lab/              # Lab databases
│   ├── docker-compose.yml
│   ├── mysql/
│   │   └── init_lab.sql       # MySQL test data
│   └── postgres/
│       └── init_lab.sql       # PostgreSQL test data
├── backend/
│   ├── api/
│   │   └── routes/            # API endpoints
│   ├── db/
│   │   ├── init_schema.sql    # Database schema
│   │   ├── models.py          # SQLAlchemy models
│   │   └── repository.py     # Data access layer
│   ├── services/
│   │   ├── mysql_collector.py
│   │   ├── postgres_collector.py
│   │   ├── analyzer.py        # Rule-based analyzer
│   │   ├── ai_stub.py         # AI integration stub
│   │   ├── fingerprint.py     # Query normalization
│   │   └── scheduler.py       # Background jobs
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── pages/             # React pages
│   │   ├── services/          # API client
│   │   └── types/             # TypeScript types
│   ├── Dockerfile
│   ├── nginx.conf             # Production nginx config
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml         # Development compose
├── docker-compose.prod.yml    # Production compose
├── .env.prod.example          # Production env template
├── start.sh                   # Startup script
└── README.md
```

### Running Tests

#### Backend Tests

```bash
cd backend
source venv/bin/activate

# Test collectors
python test_collectors.py

# Test analyzer
python test_analyzer.py
```

#### Frontend Tests

```bash
cd frontend

# Run unit tests
npm test

# Run with coverage
npm test -- --coverage
```

### Adding New Analysis Rules

Edit [backend/services/analyzer.py](backend/services/analyzer.py):

```python
def _analyze_mysql_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
    # Add your custom rule here
    if your_condition:
        return {
            'problem': 'Your problem description',
            'root_cause': 'Why it happens',
            'suggestions': [
                {
                    'priority': 'HIGH',
                    'action': 'What to do',
                    'rationale': 'Why it helps'
                }
            ],
            'improvement_level': 'HIGH',
            'estimated_speedup': '10-50x',
            'confidence_score': 0.85
        }
```

### Integrating Real AI

Replace the stub in [backend/services/ai_stub.py](backend/services/ai_stub.py):

```python
def _openai_analysis(self, sql, explain_plan, db_type, duration_ms):
    import openai

    client = openai.OpenAI(api_key=self.api_key)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "You are a database performance expert..."
        }, {
            "role": "user",
            "content": f"Analyze this query:\n{sql}\n\nEXPLAIN:\n{explain_plan}"
        }]
    )

    return self._parse_ai_response(response.choices[0].message.content)
```

## Deployment

### Production Checklist

- [ ] Update passwords in `.env.prod`
- [ ] Configure external database connections
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Configure backup schedule
- [ ] Review log levels
- [ ] Test health checks
- [ ] Load test the system

### Security Considerations

1. **Database Passwords**: Change all default passwords
2. **Redis Password**: Enable Redis authentication
3. **Network Isolation**: Use Docker networks appropriately
4. **CORS Configuration**: Restrict allowed origins in production
5. **Rate Limiting**: Consider adding rate limiting to API
6. **Input Validation**: All inputs are validated by Pydantic

### Performance Tuning

1. **Backend Workers**: Adjust workers in [docker-compose.prod.yml](docker-compose.prod.yml) based on CPU cores
2. **Collection Interval**: Balance between freshness and overhead
3. **Database Indexes**: Ensure indexes on frequently queried columns
4. **Redis Memory**: Configure maxmemory and eviction policy
5. **Nginx Caching**: Fine-tune cache headers for static assets

### Monitoring

#### Health Checks

All services include health checks:

```bash
# Check all services
docker compose ps

# Check specific service
curl http://localhost:8000/health
```

#### Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f backend

# View last 100 lines
docker compose logs --tail=100 backend
```

#### Metrics

Access the Statistics page in the UI for:
- Total queries collected
- Queries analyzed
- Improvement distribution
- Database distribution
- Collector run history

## Troubleshooting

### Lab Databases Not Starting

```bash
# Check if ports are in use
netstat -ln | grep -E '3307|5433'

# Remove old containers
docker compose down -v
cd ai-query-lab && docker compose down -v && cd ..

# Restart
./start.sh dev
```

### Backend Can't Connect to Lab Databases

1. Check if lab databases are running: `docker ps`
2. Verify credentials in environment variables
3. Test connection manually:
```bash
# MySQL
mysql -h 127.0.0.1 -P 3307 -u root -proot

# PostgreSQL
psql -h 127.0.0.1 -p 5433 -U postgres
```

### No Queries Being Collected

1. Check collector status: `GET /api/v1/collectors/status`
2. Verify slow query logging is enabled in lab databases
3. Check collector logs: `docker compose logs backend`
4. Manually trigger collection: `POST /api/v1/collectors/mysql/collect`

### Frontend Not Loading

1. Check if backend is running: `curl http://localhost:8000/health`
2. Check nginx logs: `docker compose logs frontend`
3. Verify API URL in frontend environment variables
4. Check browser console for CORS errors

### Database Schema Issues

```bash
# Recreate internal database
docker compose down internal-db
docker volume rm sql-analizer_internal-db-data
docker compose up -d internal-db

# Or use clean command
./start.sh clean
```

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `npm test` and `python test_*.py`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- **Backend**: Follow PEP 8, use type hints
- **Frontend**: Follow ESLint rules, use TypeScript strictly
- **Commits**: Use conventional commits format

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the excellent web framework
- React and Vite for modern frontend tooling
- SQLAlchemy for powerful ORM capabilities
- Docker for containerization
- TailwindCSS for utility-first styling

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at `/docs` endpoint

## Roadmap

- [ ] AI integration (OpenAI, Anthropic, local models)
- [ ] Learning loop with user feedback
- [ ] Query rewrite suggestions
- [ ] Historical trend analysis
- [ ] Automated index recommendations
- [ ] Multi-tenant support
- [ ] Grafana dashboards
- [ ] Slack/email notifications
- [ ] Query execution simulation