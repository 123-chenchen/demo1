# PDF Chatbot Backend

The backend project is contained in `backend/`. It provides a FastAPI API for authentication, notebook management, PDF upload and ingestion, retrieval, and chatbot responses.

## Directory Structure

```text
backend/
|-- app/
|   |-- api/
|   |   |-- routers.py        # FastAPI route handlers
|   |   |-- crud_router.py
|   |   `-- router.py
|   |-- config.py             # runtime settings
|   |-- crud.py               # CRUD helpers
|   |-- db/
|   |   |-- models/           # SQLAlchemy database models
|   |   |-- base.py
|   |   `-- session.py
|   |-- schemas.py            # Pydantic request/response models
|   |-- services/
|   |   |-- ai/               # chat answer generation
|   |   |-- auth/             # login, OTP, notebook ownership
|   |   |-- chatbot/          # ask flow orchestration and history
|   |   |-- documents/        # PDF upload metadata and storage handoff
|   |   |-- retrieval/        # PDF ingestion, chunking, embedding, vector search
|   |   `-- storage/          # MinIO object access
|   |-- utils/                # shared PDF helpers
|   |-- __init__.py
|   `-- main.py
|-- migrations/
|   |-- versions/
|   |-- env.py
|   `-- script.py.mako
|-- tests/
|-- alembic.ini
|-- Dockerfile
|-- main.py
|-- pyproject.toml
`-- uv.lock
```

Runtime logs, virtual environments, Python caches, and local service output are intentionally ignored by git.

## Data Model

The backend uses PostgreSQL with these main groups:

- Authentication and workspace: `users`, `notebooks`, `pending_registrations`, `email_otps`, `refresh_tokens`
- Document ingestion: `documents`, `document_contents`, `document_chunks`
- Chat history: `chat_sessions`, `chat_messages`
- Retrieval trace: `message_sources`

Detailed schema documentation is in `docs/database.md`.

## Running With Docker Compose

From the repository root:

```bash
cp .env.example .env
docker compose up -d --build
docker exec -it pdf-chatbot-ollama ollama pull qwen2.5:7b-instruct
```

The server runs at `http://127.0.0.1:8000`.

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Healthcheck: `http://127.0.0.1:8000/health`
- MinIO API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`
- Qdrant API: `http://127.0.0.1:6333`

## Running The Backend Locally

From the repository root:

```bash
cp .env.example .env
docker compose up -d postgres minio qdrant
cd backend
uv sync
uv run alembic upgrade head
uv run pdf-chatbot
```

Useful commands:

```bash
uv run alembic current
uv run alembic revision --autogenerate -m "add new table"
uv run python main.py
uv run uvicorn app.main:app --reload
uv run pytest -m "not integration"
```

The backend reads environment variables from `.env` in `backend/` when present, then falls back to `.env` in the repository root.

## Docker Compose Behavior

When run through Docker Compose, the backend service:

- waits for Postgres to become healthy
- waits for MinIO, Qdrant, and Ollama to start
- runs `alembic upgrade head`
- serves FastAPI on port `8000`

Inside Docker Compose, the backend talks to:

- Postgres through `postgres:5432`
- Qdrant through `http://qdrant:6333`
- MinIO through `minio:9000`
- Ollama through the configured `OLLAMA_BASE_URL`

## Public API

Most endpoints live under `/api`.

Authentication:

- `POST /api/auth/register/request`
- `POST /api/auth/register/verify`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password/request`
- `POST /api/auth/forgot-password/verify`

Notebooks:

- `GET /api/notebooks`
- `POST /api/notebooks`
- `GET /api/notebooks/{item_id}`
- `PATCH /api/notebooks/{item_id}`

Documents:

- `GET /api/documents`
- `GET /api/documents/{item_id}`
- `PATCH /api/documents/{item_id}`
- `DELETE /api/documents/{item_id}`
- `POST /api/documents/upload`
- `POST /api/documents/{document_id}/ingest`
- `GET /api/document-contents`
- `GET /api/document-contents/{item_id}`

Chat:

- `GET /api/chat-sessions`
- `POST /api/chat-sessions`
- `GET /api/chat-sessions/{item_id}`
- `PATCH /api/chat-sessions/{item_id}`
- `DELETE /api/chat-sessions/{item_id}`
- `POST /api/chatbot/ask`

## Authentication Notes

- Registration uses email OTP verification.
- Users are created only after OTP verification succeeds.
- Login is allowed only for verified users.
- `GET /api/auth/me` returns the current user from a Bearer access token.
- Password reset uses an email OTP.
- Refresh tokens are handled internally and are not exposed as public CRUD resources.
- `users` is an internal table and is not exposed as a public CRUD resource.

## Document And Retrieval Notes

- `documents`, `document_contents`, `document_chunks`, and `chat_sessions` are scoped by notebook for authenticated users.
- Unauthenticated requests only see public documents and sessions with no notebook.
- `POST /api/documents/upload` accepts a PDF file as `multipart/form-data`, uploads it to MinIO, extracts text with `pypdf`, chunks the text, stores rows in PostgreSQL, and indexes vectors in Qdrant.
- `POST /api/documents/{document_id}/ingest` reruns extraction, chunking, embedding, and indexing for an existing document.
- `document_chunks` and retrieval internals are not exposed as public CRUD endpoints.

## PDF Chatbot Flow

The PDF chatbot pipeline is intentionally split by responsibility:

1. Route layer: `app/api/routers.py` receives `POST /api/documents/upload`, resolves the optional notebook, and delegates to `document_upload_service`.
2. Upload service: `app/services/documents/upload.py` normalizes the filename, validates the PDF signature, reads file size/page count through `app/utils/pdf.py`, uploads the binary to MinIO through `app/services/storage/`, saves the `documents` row, then triggers ingestion.
3. PDF read step: `app/services/retrieval/ingestion.py` downloads the object from MinIO and calls `extract_pdf_pages` in `app/utils/pdf.py` to extract page text with `pypdf`.
4. Chunking step: `app/services/retrieval/chunking.py` uses the configured chunk size and overlap to split page text and count tokens.
5. Embedding step: `app/services/retrieval/embedding.py` loads the configured SentenceTransformers/HuggingFace embedding model and exposes the vector dimension.
6. Vector indexing: `app/services/retrieval/vector_store.py` ensures the Qdrant collection exists, converts chunks to LangChain documents, and upserts vectors.
7. Vector search: `app/services/retrieval/service.py` receives the user query, calls Qdrant similarity search, and converts results into `ChunkCandidate` objects.
8. Chat response: `app/services/chatbot/service.py` validates document/notebook access, runs retrieval, repairs a missing vector index when possible, calls `app/services/ai/generation.py`, and optionally stores chat messages plus source citations.

The public API and run commands stay the same after the refactor.

## Environment Variables

```env
API_HOST=0.0.0.0
API_PORT=8000
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pdf_chatbot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pdf_chatbot
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=document_chunks
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=pdf-documents
MINIO_SECURE=false
DOCUMENT_CHUNK_SIZE=1000
DOCUMENT_CHUNK_OVERLAP=200
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
RETRIEVAL_TOP_K=5
CHAT_PROVIDER=ollama
CHAT_TEMPERATURE=0.1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=qwen2.5:7b-instruct
GOOGLE_MODEL_NAME=
GOOGLE_API_KEY=
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_EXPIRE_MINUTES=10
OTP_LENGTH=6
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_STARTTLS=true
```

If the default chat provider is Ollama, pull the configured model before asking questions:

```bash
docker exec -it pdf-chatbot-ollama ollama pull qwen2.5:7b-instruct
```
