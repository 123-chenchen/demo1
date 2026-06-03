# Scripts

Place repeatable project automation here, such as local setup, data maintenance, release, or deployment helpers.

Current common commands:

```bash
docker compose up -d --build
cd backend && uv run pytest -m "not integration"
cd frontend && npm run build
```

## Run Locally Without Docker

These scripts run only the app processes. PostgreSQL, MinIO, Qdrant, and Ollama must already be running locally and match `.env`.

```powershell
.\scripts\start-local.ps1
.\scripts\stop-local.ps1
```

Run one side only:

```powershell
.\scripts\start-backend-local.ps1
.\scripts\start-frontend-local.ps1
```

Useful flags:

```powershell
.\scripts\start-local.ps1 -SkipInstall -SkipMigrations
.\scripts\start-local.ps1 -SkipDependencyCheck
.\scripts\start-backend-local.ps1 -Port 8000 -NoReload
.\scripts\start-frontend-local.ps1 -Port 5173 -ApiProxyTarget http://127.0.0.1:8000
```
