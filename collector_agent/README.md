# DBPower AI Cloud - Collector Agent

Standalone agent that monitors external databases and collects slow queries.

## Features

- **Multi-Database Support**: MySQL and PostgreSQL
- **Heartbeat Mechanism**: Sends heartbeats every 30 seconds to indicate online status
- **Remote Control**: Receives commands from backend (start, stop, collect)
- **Auto-Collection**: Automatically collects slow queries at configured intervals
- **Error Handling**: Robust error handling and automatic reconnection
- **Statistics Tracking**: Tracks queries collected, errors, and uptime

## Installation

### Prerequisites

- Python 3.8+
- Access to a MySQL or PostgreSQL database
- DBPower AI Cloud backend running

### Steps

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Register collector with backend:**

Use the backend API or admin panel to register a new collector and get the API key:

```bash
curl -X POST 'http://localhost:8000/api/v1/collectors/register' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Production MySQL Server",
    "type": "mysql",
    "team_id": 1,
    "config": {
      "host": "mysql.example.com",
      "port": 3306,
      "user": "monitoring",
      "password": "secret"
    },
    "collection_interval_minutes": 5,
    "auto_collect": true
  }'
```

Response will include `id` and `api_key`. **Save the API key!**

3. **Create configuration file:**

Copy `config.example.json` to `config.json` and fill in your details:

```json
{
  "collector_id": 1,
  "api_key": "collector_1_abc123...",
  "backend_url": "http://localhost:8000",
  "db_type": "mysql",
  "db_config": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "admin"
  },
  "heartbeat_interval": 30,
  "collection_interval": 300
}
```

### Configuration Fields

- **collector_id** (required): Collector ID from backend registration
- **api_key** (required): API key from backend registration
- **backend_url** (required): Backend API URL (e.g., `http://localhost:8000`)
- **db_type** (required): Database type (`mysql` or `postgres`)
- **db_config** (required): Database connection details
  - **host**: Database host
  - **port**: Database port (3306 for MySQL, 5432 for PostgreSQL)
  - **user**: Database user
  - **password**: Database password
  - **database**: Database name (PostgreSQL only)
  - **min_exec_time_ms**: Minimum execution time in ms (PostgreSQL only, default: 500)
- **heartbeat_interval**: Heartbeat interval in seconds (default: 30)
- **collection_interval**: Collection interval in seconds (default: 300 = 5 minutes)

## Usage

### Run the agent:

```bash
python collector_agent.py --config config.json
```

### Command-line options:

```bash
python collector_agent.py --config config.json \
  --collector-id 1 \
  --api-key collector_1_abc123... \
  --backend-url http://localhost:8000
```

Command-line arguments override configuration file values.

### Run as a service (systemd):

Create `/etc/systemd/system/dbpower-collector.service`:

```ini
[Unit]
Description=DBPower AI Cloud Collector Agent
After=network.target

[Service]
Type=simple
User=dbpower
WorkingDirectory=/opt/dbpower-collector
ExecStart=/usr/bin/python3 /opt/dbpower-collector/collector_agent.py --config /opt/dbpower-collector/config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dbpower-collector
sudo systemctl start dbpower-collector
sudo systemctl status dbpower-collector
```

## Architecture

### Communication Flow

1. **Registration**: Collector is registered with backend via API (manual step)
2. **Startup**: Agent starts and sends first heartbeat
3. **Heartbeat Loop**: Every 30 seconds:
   - Send heartbeat with stats
   - Receive pending commands from backend
   - Execute commands (start, stop, collect, update_config)
4. **Collection Loop**: Every N minutes (configurable):
   - Connect to database
   - Query slow query log (MySQL) or pg_stat_statements (PostgreSQL)
   - Send queries to backend API
5. **Monitoring**: Backend marks collector as OFFLINE if no heartbeat for 2 minutes

### Commands

The agent supports these commands from the backend:

- **start**: Enable automatic collection
- **stop**: Disable automatic collection
- **collect**: Trigger immediate collection
- **update_config**: Update database configuration

Commands are sent via backend API and retrieved during heartbeat.

## Database Configuration

### MySQL

Ensure MySQL slow query log is enabled:

```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;  -- Log queries > 0.5 seconds
SET GLOBAL log_output = 'TABLE';   -- Log to mysql.slow_log table
```

Grant permissions:

```sql
CREATE USER 'monitoring'@'%' IDENTIFIED BY 'password';
GRANT SELECT ON mysql.slow_log TO 'monitoring'@'%';
FLUSH PRIVILEGES;
```

### PostgreSQL

Enable pg_stat_statements extension:

```sql
-- In postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all

-- Restart PostgreSQL, then:
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Grant permissions:

```sql
CREATE USER monitoring WITH PASSWORD 'password';
GRANT pg_read_all_stats TO monitoring;
```

## Troubleshooting

### Agent not connecting to backend

- Check `backend_url` is correct and reachable
- Verify API key is valid
- Check backend logs for authentication errors

### No queries being collected

- Verify database slow query log is enabled (MySQL)
- Verify pg_stat_statements extension is installed (PostgreSQL)
- Check database user has necessary permissions
- Review agent logs for connection errors

### Agent shows as OFFLINE in backend

- Check agent is running: `ps aux | grep collector_agent`
- Verify heartbeat is being sent (check agent logs)
- Check network connectivity to backend
- Ensure API key is valid

### View agent logs

```bash
# If running as systemd service
sudo journalctl -u dbpower-collector -f

# If running in terminal
python collector_agent.py --config config.json 2>&1 | tee collector.log
```

## Development

### Testing locally

1. Start backend: `docker compose up backend`
2. Register collector via API
3. Create `config.json` with local settings
4. Run agent: `python collector_agent.py --config config.json`

### Testing with Docker

See `Dockerfile` and `docker-compose.yml` for containerized deployment.

## Security

- **API Keys**: Keep API keys secure. They provide full access to collector operations.
- **Database Credentials**: Store database credentials securely. Consider using environment variables or secret management tools.
- **Network**: Use HTTPS for backend_url in production
- **Permissions**: Grant minimal database permissions (read-only access to slow query logs)

## License

Part of DBPower AI Cloud project.
