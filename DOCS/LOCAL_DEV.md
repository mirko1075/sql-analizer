# Local Development (no Docker)

This document explains how to run the backend and supporting services locally without Docker. It focuses on a minimal, repeatable workflow for development and troubleshooting.

Prerequisites
- Python 3.12, python3-venv
- PostgreSQL (initdb/pg_ctl) or Docker (fallback)
- Redis (redis-server) or Docker (fallback)

Quick start (automatic)
1. Prepare the workspace and install dependencies:

```bash
./scripts/devctl.sh setup
```

2. Initialize lab DB (optional/heavy):

```bash
./scripts/devctl.sh lab-init --yes
```

3. Start the backend and scheduler locally:

```bash
./scripts/devctl.sh start-local
```

4. Stop local services:

```bash
./scripts/devctl.sh stop-local
```

Where to find logs
- Backend: `run/logs/backend.log`
- Scheduler: `run/logs/scheduler.log`
- Lab DB init: `run/logs/lab-db-init.log`

If a required system service is missing, the setup script will attempt Docker fallback. See TROUBLESHOOTING.md in `DOCS/` for common errors.
# Local development quickstart

This document explains how to bring up the full development stack locally and common troubleshooting steps.

Prerequisites
- Docker and docker-compose v2 (the `docker compose` command)
- Bash (Linux / WSL / macOS)

Environment files
- Copy the example env file to `.env` at the repository root and update values as needed. An example is provided in `.env.example` and `.env.lab` for the lab DB.

Quick commands
- Start the main stack (postgres internal DB, redis, backend, frontend):

```bash
./scripts/start-local.sh
```

- Start the main stack + lab MySQL dataset (adds the heavy MySQL lab DB):

```bash
./scripts/start-local.sh --lab-db
```

- Stop and remove containers/volumes for the stacks you started:

```bash
./scripts/stop-local.sh
# or with lab DB
./scripts/stop-local.sh --lab-db
```

Viewing logs

Use docker compose with the same set of files to stream logs. Example for main stack:

```bash
docker compose -f docker-compose.yml logs -f
```

Troubleshooting
- If a container fails to start because a container with the same name already exists, stop/remove it first:

```bash
docker ps -a
docker stop <container>
docker rm <container>
```

- If the backend shows "Could not import module 'main'", ensure you're using in-container imports that match the mounted path. The repository uses package-local imports (see `backend/`), and the backend service mounts the repo root at `/app`.

- If the database files cause permission issues, you may need to chown the volumes to the container's user. For example (Linux):

```bash
sudo chown -R 1000:1000 data/mysql
```

API endpoints added
- POST /api/v1/context/query — accepts JSON {"query": "..."} and returns top semantic matches.
- POST /api/v1/ideas/analyze — accepts JSON {"idea_text": "..."} and returns structured JSON analysis produced by the configured AI provider.

Local (no Docker) mode
-----------------------

If you prefer to run services without Docker, use the interactive helper script `scripts/run-batch.sh`. The script will ask which mode (docker/local) and which services to start. It supports starting:

- internal-db (local Postgres on port 5440)
- redis (local redis-server on port 6379)
- backend (starts Uvicorn with auto-reload on port 8000)
- scheduler (runs `backend/services/scheduler.py` which will invoke collectors)
- mysql-lab (attempts to start a local mysqld on port 3307)
- postgres-lab (attempts to start a separate local Postgres on port 5433)

Prerequisites for local mode (non-Docker):

- System binaries: `initdb`/`pg_ctl`/`postgres` for Postgres, `mysqld` for MySQL, `redis-server` for Redis, `uvicorn` and a Python venv with backend deps installed.
- Ensure `backend/requirements.txt` is installed into the project's venv (you can create `.venv` at the repo root and install there).

Example usage:

```bash
# Interactive: select local mode and pick services
./scripts/run-batch.sh

# After starting, tail the backend log
tail -f run/logs/backend.log
```

Notes and caveats
- Local mode attempts to create per-service data directories under `data/` (e.g. `data/internal-db-local`). These are not the same as Docker volumes and will be owned by the user that runs the commands.
- Local mode is intended for development and quick testing. Some features (healthchecks, networking isolation) are easier with Docker.
- If you don't have the system binaries installed or you prefer an easier path, use Docker mode instead.
