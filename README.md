# Workspace Layout

The root directory only keeps files required to run the full local stack. Backend and frontend code live in separate folders.

```text
demo1/
|-- .env.example
|-- docker-compose.yml
|-- docs/
|   |-- backend.md
|   |-- frontend.md
|   `-- database.md
|-- scripts/
|-- backend/
`-- frontend/
```

Docker Compose currently runs:

- `postgres`
- `minio`
- `qdrant`
- `ollama`
- `backend` FastAPI at `http://127.0.0.1:8000`
- `frontend` at `http://127.0.0.1:5173`, with `/api` proxied to the backend inside Docker

Detailed documentation:

- Backend: `docs/backend.md`
- Frontend: `docs/frontend.md`
- Database schema: `docs/database.md`
