# Collector Agent Deployment Guide

## Deployment Options

### Option 1: Standalone Python Process

Best for: Development, testing, simple deployments

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create configuration:**
   ```bash
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

3. **Run the agent:**
   ```bash
   python collector_agent.py --config config.json
   ```

### Option 2: Docker Container (Standalone)

Best for: Production, isolated environments

1. **Build Docker image:**
   ```bash
   docker build -t dbpower-collector:latest .
   ```

2. **Create configuration:**
   ```bash
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

3. **Run container:**
   ```bash
   docker run -d \
     --name dbpower-collector \
     --restart unless-stopped \
     -v $(pwd)/config.json:/app/config/config.json:ro \
     --network dbpower-ai-cloud_dbpower-network \
     dbpower-collector:latest
   ```

4. **View logs:**
   ```bash
   docker logs -f dbpower-collector
   ```

### Option 3: Docker Compose

Best for: Multiple collectors, orchestrated deployments

1. **Create configurations for each collector:**
   ```bash
   cp config.example.json config-mysql.json
   cp config.example.json config-postgres.json
   # Edit each config file
   ```

2. **Start collectors:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f collector-mysql
   docker-compose logs -f collector-postgres
   ```

### Option 4: Add to Main Docker Compose

Best for: Integrated deployment with backend

Add this to the main `docker-compose.yml`:

```yaml
  # Collector Agent - MySQL Production Server
  collector-mysql-prod:
    build:
      context: ./collector_agent
      dockerfile: Dockerfile
    container_name: collector-mysql-prod
    restart: unless-stopped
    volumes:
      - ./collector_agent/config-mysql-prod.json:/app/config/config.json:ro
    environment:
      - TZ=UTC
    networks:
      - dbpower-network
    depends_on:
      - backend
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Collector Agent - PostgreSQL Analytics
  collector-postgres-analytics:
    build:
      context: ./collector_agent
      dockerfile: Dockerfile
    container_name: collector-postgres-analytics
    restart: unless-stopped
    volumes:
      - ./collector_agent/config-postgres-analytics.json:/app/config/config.json:ro
    environment:
      - TZ=UTC
    networks:
      - dbpower-network
    depends_on:
      - backend
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Then start everything:

```bash
cd /path/to/dbpower-ai-cloud
docker compose up -d
```

## Configuration Management

### Environment-Specific Configs

Create separate config files for each environment:

```
collector_agent/
├── config.example.json          # Template
├── config-dev-mysql.json         # Development MySQL
├── config-staging-mysql.json    # Staging MySQL
├── config-prod-mysql.json       # Production MySQL
├── config-prod-postgres.json    # Production PostgreSQL
```

### Secret Management

**Option 1: Environment Variables**

Modify `collector_agent.py` to read from environment variables:

```python
# In your config.json, use placeholders
{
  "api_key": "${API_KEY}",
  "db_config": {
    "password": "${DB_PASSWORD}"
  }
}
```

**Option 2: Docker Secrets (Swarm)**

```yaml
services:
  collector-mysql:
    secrets:
      - collector_api_key
      - db_password
    environment:
      - API_KEY_FILE=/run/secrets/collector_api_key
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  collector_api_key:
    external: true
  db_password:
    external: true
```

**Option 3: HashiCorp Vault / AWS Secrets Manager**

Use appropriate SDKs to fetch secrets at runtime.

## Scaling

### Multiple Collectors

You can run multiple collector agents for:

1. **Different databases**: One collector per database server
2. **High availability**: Multiple collectors for the same database (with different collection intervals)
3. **Geographic distribution**: Collectors close to their target databases

Example:

```bash
# Collector 1: MySQL Production (US East)
docker run -d --name collector-mysql-us-east \
  -v ./config-mysql-us-east.json:/app/config/config.json:ro \
  dbpower-collector:latest

# Collector 2: MySQL Production (EU West)
docker run -d --name collector-mysql-eu-west \
  -v ./config-mysql-eu-west.json:/app/config/config.json:ro \
  dbpower-collector:latest

# Collector 3: PostgreSQL Analytics
docker run -d --name collector-postgres-analytics \
  -v ./config-postgres-analytics.json:/app/config/config.json:ro \
  dbpower-collector:latest
```

## Monitoring

### Health Checks

**Docker health check:**

```bash
docker inspect --format='{{.State.Health.Status}}' dbpower-collector
```

**Backend API health:**

```bash
curl 'http://localhost:8000/api/v1/collectors' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN'
```

Check `is_online` field for each collector.

### Logs

**Docker logs:**

```bash
docker logs -f dbpower-collector --tail 100
```

**Systemd logs:**

```bash
sudo journalctl -u dbpower-collector -f
```

### Metrics

The agent reports these metrics via heartbeat:

- `queries_collected`: Total queries collected
- `errors_count`: Total errors encountered
- `uptime_seconds`: Collector uptime
- `last_error`: Last error message

Access via backend API:

```bash
curl 'http://localhost:8000/api/v1/collectors/{id}' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN'
```

## Troubleshooting

### Collector shows as OFFLINE

1. Check agent is running:
   ```bash
   docker ps | grep collector
   # or
   ps aux | grep collector_agent
   ```

2. Check agent logs for errors:
   ```bash
   docker logs dbpower-collector --tail 50
   ```

3. Verify network connectivity:
   ```bash
   docker exec dbpower-collector curl http://backend:8000/health
   ```

4. Verify API key is valid:
   ```bash
   # Check config.json
   cat config.json | grep api_key
   ```

### Database connection errors

1. Verify database is accessible:
   ```bash
   # MySQL
   docker exec dbpower-collector mysql -h $DB_HOST -u $DB_USER -p$DB_PASS -e "SELECT 1"

   # PostgreSQL
   docker exec dbpower-collector psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"
   ```

2. Check database permissions:
   ```sql
   -- MySQL
   SHOW GRANTS FOR 'monitoring'@'%';

   -- PostgreSQL
   \du monitoring
   ```

3. Verify slow query log is enabled:
   ```sql
   -- MySQL
   SHOW VARIABLES LIKE 'slow_query_log';

   -- PostgreSQL
   SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';
   ```

### No queries being collected

1. Check collection interval:
   ```json
   {
     "collection_interval": 300  // 5 minutes
   }
   ```

2. Check if queries meet threshold:
   ```sql
   -- MySQL: Check long_query_time
   SHOW VARIABLES LIKE 'long_query_time';

   -- PostgreSQL: Check min_exec_time_ms in config
   ```

3. Manually trigger collection:
   ```bash
   curl -X POST 'http://localhost:8000/api/v1/collectors/{id}/collect' \
     -H 'Authorization: Bearer YOUR_JWT_TOKEN'
   ```

### High memory usage

If collector is using too much memory:

1. Reduce collection batch size (modify `LIMIT` in agent code)
2. Increase collection interval
3. Add memory limits in Docker:

   ```bash
   docker run --memory=256m --memory-swap=512m ...
   ```

## Production Checklist

- [ ] Use HTTPS for backend_url
- [ ] Store API keys securely (secrets management)
- [ ] Use read-only database user
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Test failover scenarios
- [ ] Document recovery procedures
- [ ] Set memory/CPU limits
- [ ] Use restart policies
- [ ] Enable health checks
- [ ] Regular config backups

## Security Best Practices

1. **Minimal Permissions**: Grant only SELECT on slow query tables
2. **Network Isolation**: Use private networks, avoid public exposure
3. **API Key Rotation**: Rotate API keys regularly
4. **TLS**: Use HTTPS for all backend communication
5. **Audit Logging**: Enable audit logs on database
6. **Container Security**: Run as non-root user (already configured)
7. **Secret Management**: Never commit secrets to git

## Backup and Recovery

### Backup Configuration

```bash
# Backup all collector configs
tar -czf collector-configs-backup-$(date +%Y%m%d).tar.gz \
  collector_agent/config*.json
```

### Disaster Recovery

1. **Collector Agent Lost**:
   - Redeploy agent with same config
   - Agent will automatically reconnect on next heartbeat

2. **API Key Lost**:
   - Cannot recover original key
   - Must delete old collector and create new one
   - Update agent config with new API key

3. **Backend Lost**:
   - Agents will continue attempting to connect
   - Once backend is restored, agents will reconnect automatically

## Upgrading

### Agent Upgrade

1. Stop collector:
   ```bash
   docker stop dbpower-collector
   ```

2. Pull new image:
   ```bash
   docker pull dbpower-collector:latest
   ```

3. Start collector:
   ```bash
   docker start dbpower-collector
   ```

4. Verify:
   ```bash
   docker logs dbpower-collector --tail 20
   ```

### Zero-Downtime Upgrade (Multiple Collectors)

If running multiple collectors for the same database:

1. Upgrade collector 1
2. Wait for it to come online
3. Upgrade collector 2
4. Repeat for all collectors

## Support

For issues or questions:

- GitHub Issues: https://github.com/your-org/dbpower-ai-cloud/issues
- Documentation: https://docs.dbpower.ai
- Slack: #dbpower-support
