# AI Query Analyzer - Backend API

FastAPI-based REST API for collecting, analyzing, and optimizing slow SQL queries.

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── api/
│   ├── routes/
│   │   ├── slow_queries.py # Slow query endpoints
│   │   └── stats.py        # Statistics endpoints
│   └── schemas/
│       ├── slow_query.py   # Pydantic models for queries
│       └── stats.py        # Pydantic models for stats
├── core/
│   ├── config.py          # Configuration management
│   └── logger.py          # Logging setup
├── db/
│   ├── models.py          # SQLAlchemy ORM models
│   ├── session.py         # Database session management
│   └── init_schema.sql    # PostgreSQL schema
└── services/              # Business logic (collectors, analyzers)
```

## API Endpoints

### Health & Info

- `GET /` - API information
- `GET /health` - Health check with dependency status
- `GET /docs` - OpenAPI/Swagger documentation
- `GET /redoc` - ReDoc documentation

### Slow Queries

- `GET /api/v1/slow-queries` - List slow queries (paginated, filterable)
- `GET /api/v1/slow-queries/{id}` - Get query details with analysis
- `GET /api/v1/slow-queries/fingerprint/{hash}` - Get queries by fingerprint
- `DELETE /api/v1/slow-queries/{id}` - Delete a query

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 200)
- `source_db_type`: Filter by database type (mysql, postgres)
- `source_db_host`: Filter by database host
- `min_duration_ms`: Minimum query duration
- `status`: Filter by status (NEW, ANALYZED, IGNORED, ERROR)

### Statistics

- `GET /api/v1/stats/top-tables` - Most impacted tables
- `GET /api/v1/stats/database/{type}/{host}` - Database-specific stats
- `GET /api/v1/stats/global` - Global statistics across all databases
- `GET /api/v1/stats/databases` - List monitored databases

## Running Locally (Development)

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ (internal database)
- Redis 7+

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Set Environment Variables

Copy `.env.example` to `.env` and configure:

```env
INTERNAL_DB_HOST=localhost
INTERNAL_DB_PORT=5440
INTERNAL_DB_USER=ai_core
INTERNAL_DB_PASSWORD=ai_core
INTERNAL_DB_NAME=ai_core

REDIS_HOST=localhost
REDIS_PORT=6379
```

### Run the Server

```bash
# Option 1: Using Python directly
python main.py

# Option 2: Using uvicorn with auto-reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using uvicorn with specific settings
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access the API

- **API Root:** http://localhost:8000/
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Running with Docker

### Build the Image

```bash
cd backend
docker build -t ai-analyzer-backend .
```

### Run the Container

```bash
docker run -d \
  --name ai-analyzer-backend \
  -p 8000:8000 \
  -e INTERNAL_DB_HOST=internal-db \
  -e INTERNAL_DB_PORT=5432 \
  -e INTERNAL_DB_USER=ai_core \
  -e INTERNAL_DB_PASSWORD=ai_core \
  -e INTERNAL_DB_NAME=ai_core \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  --network ai-analyzer-network \
  ai-analyzer-backend
```

### Run with Docker Compose

From the project root:

```bash
docker compose up -d backend
```

## API Usage Examples

### List Slow Queries

```bash
curl http://localhost:8000/api/v1/slow-queries?page=1&page_size=10
```

### Get Query Details

```bash
curl http://localhost:8000/api/v1/slow-queries/{query-id}
```

### Filter by Database

```bash
curl "http://localhost:8000/api/v1/slow-queries?source_db_type=mysql&source_db_host=mysql-lab"
```

### Get Global Statistics

```bash
curl http://localhost:8000/api/v1/stats/global
```

### Get Top Impacted Tables

```bash
curl http://localhost:8000/api/v1/stats/top-tables?limit=10
```

## Response Formats

### Slow Query Summary

```json
{
  "items": [
    {
      "fingerprint": "SELECT * FROM orders WHERE status = ?",
      "source_db_type": "mysql",
      "source_db_host": "mysql-lab",
      "execution_count": 42,
      "avg_duration_ms": 1234.56,
      "min_duration_ms": 890.12,
      "max_duration_ms": 2345.67,
      "p95_duration_ms": 2100.00,
      "last_seen": "2025-10-31T10:00:00",
      "has_analysis": true,
      "max_improvement_level": "HIGH"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "total_pages": 2
}
```

### Query Details with Analysis

```json
{
  "id": "uuid-here",
  "source_db_type": "mysql",
  "source_db_host": "mysql-lab",
  "fingerprint": "SELECT * FROM orders WHERE status = ?",
  "full_sql": "SELECT * FROM orders WHERE status = 'SHIPPED'",
  "duration_ms": 1234.56,
  "rows_examined": 500000,
  "rows_returned": 1000,
  "plan_json": { ...execution plan... },
  "status": "ANALYZED",
  "analysis": {
    "problem": "Full table scan on large table",
    "root_cause": "Missing index on status column",
    "suggestions": [
      {
        "type": "INDEX",
        "priority": "HIGH",
        "sql": "CREATE INDEX idx_orders_status ON orders(status)",
        "description": "Add index on status column to avoid full table scan",
        "estimated_impact": "50-100x improvement"
      }
    ],
    "improvement_level": "HIGH",
    "estimated_speedup": "50x"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (development/production) | development |
| `LOG_LEVEL` | Logging level | INFO |
| `INTERNAL_DB_HOST` | Internal PostgreSQL host | localhost |
| `INTERNAL_DB_PORT` | Internal PostgreSQL port | 5440 |
| `INTERNAL_DB_USER` | Database user | ai_core |
| `INTERNAL_DB_PASSWORD` | Database password | ai_core |
| `INTERNAL_DB_NAME` | Database name | ai_core |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `MYSQL_HOST` | MySQL lab host | 127.0.0.1 |
| `MYSQL_PORT` | MySQL lab port | 3307 |
| `PG_HOST` | PostgreSQL lab host | 127.0.0.1 |
| `PG_PORT` | PostgreSQL lab port | 5433 |

## Development

### Code Style

The project follows:
- PEP 8 style guide
- Type hints for all functions
- Docstrings for all public APIs

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=backend --cov-report=html
```

### Code Quality

```bash
# Format code
black backend/

# Lint
flake8 backend/

# Type check
mypy backend/
```

## Database Models

### SlowQueryRaw

Stores collected slow queries from target databases.

**Fields:**
- `id` (UUID): Primary key
- `source_db_type`: Database type (mysql, postgres, etc.)
- `source_db_host`: Database host
- `fingerprint`: Normalized query pattern
- `full_sql`: Original SQL query
- `duration_ms`: Execution time
- `rows_examined`: Rows scanned
- `rows_returned`: Result rows
- `plan_json`: Execution plan (JSON)
- `status`: Processing status
- `captured_at`: When query was captured

### AnalysisResult

Stores AI-generated analysis and optimization suggestions.

**Fields:**
- `id` (UUID): Primary key
- `slow_query_id`: Foreign key to SlowQueryRaw
- `problem`: Problem description
- `root_cause`: Technical explanation
- `suggestions`: Array of optimization suggestions (JSON)
- `improvement_level`: Impact level (LOW/MEDIUM/HIGH/CRITICAL)
- `estimated_speedup`: Expected performance gain

### Views

- `query_performance_summary`: Aggregated query statistics by fingerprint
- `impactful_tables`: Tables appearing most in slow queries

## Troubleshooting

### Database Connection Failed

```bash
# Check if internal-db is running
docker ps | grep ai-analyzer-internal-db

# Test connection
docker exec ai-analyzer-internal-db pg_isready -U ai_core
```

### Redis Connection Failed

```bash
# Check if Redis is running
docker ps | grep ai-analyzer-redis

# Test connection
docker exec ai-analyzer-redis redis-cli ping
```

### Import Errors

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

- **STEP 4:** Implement collector service to gather slow queries from lab databases
- **STEP 5:** Implement analyzer service to generate optimization suggestions
- **STEP 6:** Build React frontend to visualize the data

## License

Internal project - AI Query Analyzer
