## Troubleshooting

Common issues when running locally:

- ModuleNotFoundError: ensure you run with `PYTHONPATH=.` or start from repo root and activate `.venv`.
- PermissionError from watchfiles: change ownership of `data/` to your user or limit uvicorn `--reload-dir` to `backend/`.
- UndefinedTable errors: run lab DB init or create schema before starting services.
- Missing system services (Postgres/Redis): either install them or let the setup script use Docker fallback.

Logs are in `run/logs/` — check backend.log and scheduler.log first.
