# DBPower Collector Agent

On-premise collector agent that monitors MySQL and PostgreSQL databases and sends slow query metrics to the DBPower SaaS backend.

## Features

- Collects slow queries from MySQL (via `performance_schema`)
- Collects slow queries from PostgreSQL (via `pg_stat_statements`)
- Automatic heartbeat to backend
- Configurable collection intervals
- Automatic retry and error handling

## Prerequisites

### MySQL
Enable `performance_schema`:
```sql
-- Add to my.cnf or my.ini
[mysqld]
performance_schema = ON
```

### PostgreSQL
Enable `pg_stat_statements` extension:
```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- Create extension in database
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

## Usage

### Docker (Recommended)

```bash
docker run -d \
  --name dbpower-agent \
  -e DBPOWER_API_URL=https://api.dbpower.io/api/v1 \
  -e DBPOWER_AGENT_TOKEN=agt_your_token_here \
  -e COLLECTION_INTERVAL_SECONDS=300 \
  -e HEARTBEAT_INTERVAL_SECONDS=60 \
  humanaise/dbpower-agent:latest
```

### Python

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DBPOWER_API_URL=https://api.dbpower.io/api/v1
export DBPOWER_AGENT_TOKEN=agt_your_token_here

# Run agent
python agent.py
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DBPOWER_API_URL` | Yes | `http://localhost:8000/api/v1` | DBPower backend API URL |
| `DBPOWER_AGENT_TOKEN` | Yes | - | Agent authentication token (from onboarding) |
| `COLLECTION_INTERVAL_SECONDS` | No | `300` (5 minutes) | How often to collect slow queries |
| `HEARTBEAT_INTERVAL_SECONDS` | No | `60` (1 minute) | How often to send heartbeat |

## How It Works

1. **Startup**: Agent reads `DBPOWER_AGENT_TOKEN` from environment
2. **Configuration**: Fetches database list from backend via `GET /collectors/config`
3. **Collection**: Every 5 minutes (default), collects slow queries from each database
4. **Ingestion**: Sends collected queries to backend via `POST /collectors/ingest/slow-queries`
5. **Heartbeat**: Every 60 seconds (default), sends status to backend via `POST /collectors/heartbeat`

## Building

```bash
# Build Docker image
docker build -t humanaise/dbpower-agent:latest .

# Test locally
docker run --rm -it \
  -e DBPOWER_API_URL=http://host.docker.internal:8000/api/v1 \
  -e DBPOWER_AGENT_TOKEN=agt_test_token \
  humanaise/dbpower-agent:latest
```

## Logging

Agent logs to stdout with the following levels:
- `INFO`: Normal operation (collection cycles, heartbeats)
- `WARNING`: Non-fatal issues (backend errors, skipped queries)
- `ERROR`: Fatal issues (connection failures, authentication errors)

View logs:
```bash
docker logs -f dbpower-agent
```

## Troubleshooting

### Agent not collecting queries

1. **MySQL**: Ensure `performance_schema` is enabled
   ```sql
   SHOW VARIABLES LIKE 'performance_schema';
   ```

2. **PostgreSQL**: Ensure `pg_stat_statements` is loaded
   ```sql
   SELECT * FROM pg_available_extensions WHERE name = 'pg_stat_statements';
   ```

### Authentication errors

- Verify `DBPOWER_AGENT_TOKEN` is correct
- Check token hasn't expired or been revoked
- Ensure agent can reach backend API

### Connection errors

- Verify database credentials in DBPower dashboard
- Check network connectivity from agent to databases
- Ensure firewall allows agent to connect to databases

## Support

For issues or questions, contact support@dbpower.io
