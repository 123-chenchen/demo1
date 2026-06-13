# PDF Chatbot Docker Stack

This repository contains one Docker Compose stack for the PDF Chatbot application:

- `postgres` for application data
- `minio` for uploaded PDF objects
- `qdrant` for vector search
- `ollama` for local chat generation
- `backend` FastAPI API
- `frontend` nginx/Vite build, with `/api` proxied to `backend`

All services run on the same Compose network and use service names such as `postgres`, `qdrant`, `minio`, and `ollama` inside Docker.

## Environment

Copy the example file and edit secrets before deploying:

```bash
cp .env.example .env
```

Important values:

- `DATABASE_URL` must use the Docker service name `postgres`, not `localhost`.
- `QDRANT_URL` must use `http://qdrant:6333`.
- `MINIO_ENDPOINT` must use `minio:9000`.
- `OLLAMA_BASE_URL` must use `http://ollama:11434`.
- `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and MinIO credentials must be changed before production.
- Leave `FRONTEND_API_BASE_URL` empty for Docker so the frontend calls the backend through same-origin `/api`.

## First Run

```bash
docker compose up -d --build
```

The backend runs an idempotent schema bootstrap when Compose maps `BACKEND_AUTO_INIT_DB=true` to backend `AUTO_INIT_DB=true`. It creates missing tables and applies additive schema fixes without dropping existing data.

## Update Existing Deployment

Do not remove volumes during an update. Rebuild the images and restart containers:

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

## Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Do Not Use

```bash
docker compose down -v
```

That command deletes named volumes and can remove PostgreSQL, MinIO, and Qdrant data.

## Local URLs

- Frontend: `http://127.0.0.1:5173`
- Backend healthcheck: `http://127.0.0.1:8000/health`
- MinIO console: `http://127.0.0.1:9001`
- Qdrant API: `http://127.0.0.1:6333`
