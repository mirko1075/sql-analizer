# DBPower Client Agent

On-premise database monitoring agent for DBPower AI Cloud.

## Overview

The Client Agent runs on-premise at customer sites and:
- Collects slow queries from customer databases (MySQL, PostgreSQL)
- Anonymizes sensitive data before transmission
- Securely sends data to DBPower AI Cloud SaaS backend
- Supports multiple databases simultaneously

## Features

- **Multi-Database Support**: MySQL, PostgreSQL, MariaDB
- **Data Anonymization**: Three levels (strict, moderate, minimal)
- **Secure Communication**: API key authentication, TLS encryption
- **Retry Logic**: Automatic retry with exponential backoff
- **Health Checks**: Built-in monitoring and health checks
- **Docker Support**: Easy deployment with Docker/Docker Compose

## Installation

### Docker (Recommended)

1. Copy `docker-compose.yml` and edit configuration:
   ```bash
   cp docker-compose.yml my-config.yml
   nano my-config.yml
   ```

2. Start the agent:
   ```bash
   docker-compose -f my-config.yml up -d
   ```

### Manual Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create configuration file:
   ```bash
   cp config.example.json config.json
   nano config.json
   ```

3. Run the agent:
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLIENT_AGENT_ID` | Yes | Unique agent identifier |
| `SAAS_API_URL` | Yes | SaaS backend URL |
| `SAAS_API_KEY` | Yes | Organization API key (from SaaS) |
| `DB_CONNECTIONS` | Yes | JSON array of database connections |
| `ANONYMIZATION_LEVEL` | No | strict, moderate, or minimal (default: strict) |
| `LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR (default: INFO) |

### Configuration File

Alternatively, use a JSON configuration file:

```bash
export CONFIG_FILE=/path/to/config.json
python main.py
```

See `config.example.json` for format.

## Database Configuration

### MySQL

1. Enable slow query log:
   ```sql
   SET GLOBAL slow_query_log = 'ON';
   SET GLOBAL log_output = 'TABLE';
   SET GLOBAL long_query_time = 1.0;
   ```

2. Create read-only user:
   ```sql
   CREATE USER 'dbpower_readonly'@'%' IDENTIFIED BY 'secure_password';
   GRANT SELECT ON mysql.slow_log TO 'dbpower_readonly'@'%';
   FLUSH PRIVILEGES;
   ```

### PostgreSQL

1. Install pg_stat_statements:
   ```sql
   CREATE EXTENSION pg_stat_statements;
   ```

2. Configure postgresql.conf:
   ```
   shared_preload_libraries = 'pg_stat_statements'
   pg_stat_statements.track = all
   ```

3. Create read-only user:
   ```sql
   CREATE USER dbpower_readonly WITH PASSWORD 'secure_password';
   GRANT pg_read_all_stats TO dbpower_readonly;
   ```

## Anonymization Levels

### Strict (Default)
- Masks all string and numeric values
- Only preserves SQL structure
- Example: `SELECT * FROM users WHERE email = '[EMAIL_REDACTED]' AND age > [NUMBER_REDACTED]`

### Moderate
- Masks sensitive data (emails, IPs, credit cards, phone numbers)
- Preserves other values
- Example: `SELECT * FROM users WHERE email = '[EMAIL_REDACTED]' AND age > 25`

### Minimal
- Only masks obvious PII (emails, credit cards, SSNs)
- Example: `SELECT * FROM users WHERE email = '[EMAIL_REDACTED]' AND name = 'John'`

## Security

- **API Key**: Authenticates agent with SaaS backend
- **TLS Encryption**: All communication over HTTPS
- **Data Anonymization**: Sensitive data masked before transmission
- **Read-Only Access**: Agent only needs SELECT permissions
- **No Data Storage**: No local database created, cache is temporary

## Monitoring

### Health Check

The agent runs a simple health check:

```bash
docker exec dbpower-client-agent python -c "import sys; sys.exit(0)"
```

### Logs

View logs:
```bash
docker logs -f dbpower-client-agent
```

### Statistics

Statistics are logged on shutdown:
```
Final Statistics:
  Uptime: 3600s
  Collections: 60
  Queries collected: 150
  Queries anonymized: 150
  Queries sent: 150
  Errors: 0
```

## Troubleshooting

### Agent can't connect to database

1. Check database credentials
2. Verify network connectivity
3. Check firewall rules
4. Verify database slow log is enabled

### Agent can't connect to SaaS backend

1. Check `SAAS_API_URL` is correct
2. Verify `SAAS_API_KEY` is valid
3. Check network/firewall allows HTTPS outbound
4. Verify SSL certificate if using self-hosted

### No queries being collected

1. Check slow query log is enabled
2. Verify `long_query_time` threshold
3. Check database has slow queries
4. Verify read-only user has permissions

## Development

### Running Tests

```bash
cd tests
python -m pytest -v
```

### Building Docker Image

```bash
docker build -t dbpower-client-agent .
```

## Support

For issues or questions:
- GitHub: https://github.com/mirko1075/dbpower-ai-cloud/issues
- Documentation: https://docs.dbpower.cloud

## License

Copyright © 2024 DBPower AI Cloud
