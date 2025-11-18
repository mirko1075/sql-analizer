# dbpower-ai-cloud — quickstart

This repository contains the AI Query Analyzer backend and tools. The README here is intentionally minimal — developer docs and troubleshooting are in `DOCS/`.

Quick commands

1) Setup and start local (tries system services, falls back to Docker):

```bash
./scripts/devctl.sh setup
```

2) Initialize lab DB (optional heavy SQL):

```bash
./scripts/devctl.sh lab-init --yes
```

3) Start or stop local processes:

```bash
./scripts/devctl.sh start-local
./scripts/devctl.sh stop-local
```

4) Use Docker compose when preferred:

```bash
./scripts/devctl.sh docker-up
./scripts/devctl.sh docker-down
```

More detailed developer instructions and troubleshooting are in `DOCS/LOCAL_DEV.md` and `DOCS/TROUBLESHOOTING.md`.
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
# dbpower-ai-cloud — developer quickstart

This repository contains the AI Query Analyzer backend, frontend, lab databases and helper scripts.

This README is a concise developer quickstart. Full design and troubleshooting docs are in `DOCS/`.

Quick start

1. Start the full local stack (backend + scheduler + frontend) without LabDB initialization:

```bash
./scripts/devctl.sh start-all
```

1. Start the full stack and run LabDB init (heavy SQL). Use `--yes` to run non-interactively:

```bash
./scripts/devctl.sh start-all-with-lab --yes
```

Important commands (developer)

- `./scripts/devctl.sh setup` — prepare venv, install backend deps, start Postgres/Redis (or Docker fallback)
- `./scripts/devctl.sh start-local` — start backend + scheduler (no frontend)
- `./scripts/devctl.sh start-all` — start backend + scheduler + frontend (no LabDB init)
- `./scripts/devctl.sh start-all-with-lab [--yes]` — start services and run LabDB init (prompted unless `--yes`)
- `./scripts/devctl.sh lab-init [--yes]` — run lab DB init scripts (recursive search; applies .sql via psql or docker exec)
- `./scripts/devctl.sh stress-db` — run heavy queries from `tests/heavy-queries.sql` (use with caution)
- `./scripts/devctl.sh stop-local` — stop local processes started by scripts
- `./scripts/devctl.sh docker-up` / `docker-down` — start/stop docker compose stacks

Logs and runtime artifacts

- `run/logs/` — logs created by the scripts (backend.log, scheduler.log, frontend.log, lab-db-init.log, stress-db.log)
- `run/*.pid` — pidfiles for started processes (backend.pid, scheduler.pid, frontend.pid, redis.pid)

Lab DB initialization and stress tests

- Lab DB initialization can execute heavy SQL to create schemas and load test data. This is intentionally separate to avoid accidental changes.
- `scripts/run_lab_init.sh` searches the repository for candidate init scripts and `.sql` files and applies them using `psql` (or `docker exec local-postgres-dev` as a fallback).
- `scripts/stress-db.sh` runs `tests/heavy-queries.sql` and logs to `run/logs/stress-db.log`.

Frontend notes

- The frontend dev server (Vite) is started by `scripts/start-frontend-local.sh` and logs to `run/logs/frontend.log`.
- Vite default dev port is `5173`. The `devctl` commands perform a smoke-test at `http://localhost:5173` after starting the frontend.

Health checks and smoke tests

- `start-all` and `start-all-with-lab` wait for backend (port 8000) and frontend (port 5173) and run a small HTTP smoke-test against the frontend to verify it is serving.

Cleaning up

Stop local processes started by the scripts:

```bash
./scripts/devctl.sh stop-local
```

Remove runtime artifacts (pidfiles and logs):

```bash
rm -rf run/*.pid run/logs/*
```

Docker vs local

- `devctl` prefers local system services when available, but will fall back to Docker containers `local-postgres-dev` and `local-redis-dev`.
- For full production-like runs (lab databases included), use the docker-compose stacks:

```bash
./scripts/devctl.sh docker-up
./scripts/devctl.sh docker-down
```

More docs

- Developer / local setup: `DOCS/LOCAL_DEV.md`
- Troubleshooting: `DOCS/TROUBLESHOOTING.md`
- API docs: run the backend and open `http://localhost:8000/docs`

Next improvements (optional)

- Add stricter post-init schema checks (verify `slow_queries` and key tables) and fail fast
- Limit `run_lab_init.sh` to a preferred directory (e.g. `lab-database/`) rather than the whole repo

Try it

```bash
./scripts/devctl.sh start-all
# later, if you want the LabDB init:
./scripts/devctl.sh lab-init --yes
```

A couple of developer snippets

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

---


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