# PDF Chatbot Backend

Tat ca logic backend da duoc dua vao thu muc `backend/`.

## Cau truc thu muc

```text
backend/
|-- app/
|   |-- api/
|   |   |-- routers/
|   |   |-- crud_router.py
|   |   `-- router.py
|   |-- core/
|   |   `-- config.py
|   |-- crud/
|   |-- db/
|   |   |-- models/
|   |   |   |-- auth.py
|   |   |   |-- chat.py
|   |   |   |-- document.py
|   |   |   |-- shared.py
|   |   |   `-- __init__.py
|   |   |-- base.py
|   |   |-- README.md
|   |   `-- session.py
|   |-- schemas/
|   |-- __init__.py
|   `-- main.py
|-- migrations/
|   |-- versions/
|   |-- env.py
|   `-- script.py.mako
|-- alembic.ini
|-- main.py
`-- pyproject.toml
```

## Schema

- `users`: tai khoan dang nhap.
- `refresh_tokens`: luu refresh token dang hoat dong hoac da revoke.
- `documents`: moi file PDF la mot record.
- `document_contents`: luu text thô da extract tu tai lieu, 1-1 voi `documents`.
- `document_chunks`: moi doan text sau khi chunk la mot record, co `qdrant_point_id` de map sang vector trong Qdrant.
- `chat_sessions`: dai dien cho mot cuoc hoi thoai, co the gan voi `user_id`.
- `chat_messages`: luu cau hoi cua user va cau tra loi cua bot.
- `message_sources`: luu cac chunk da duoc dung de tao cau tra loi.

Tai lieu chi tiet ve database va y nghia tung attribute nam o `app/db/README.md`.

## Cach chay

`docker-compose.yml` va `.env.example` nam o root de sau nay co the them frontend/local services dung chung.

Chay bang Docker Compose:

```bash
cp .env.example .env
docker compose up -d --build
docker exec -it pdf-chatbot-ollama ollama pull qwen2.5:7b-instruct
```

Chay backend local khong dung compose:

```bash
cp .env.example .env
docker compose up -d postgres minio qdrant
cd backend
uv sync
uv run alembic upgrade head
uv run pdf-chatbot
```

Server mac dinh chay tai `http://127.0.0.1:8000`.

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Healthcheck: `http://127.0.0.1:8000/health`
- MinIO API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`
- Qdrant API: `http://127.0.0.1:6333`

## Lenh huu ich

```bash
uv run alembic current
uv run alembic revision --autogenerate -m "add new table"
uv run python main.py
uv run uvicorn app.main:app --reload
```

Backend se doc bien moi truong tu `.env` trong `backend/`, neu khong co thi se fallback sang `.env` o root.

Neu chay bang Docker Compose, service `backend` se tu dong:

- cho `postgres` healthy
- cho `minio` start xong
- cho `qdrant` start xong
- cho `ollama` start xong
- chay `alembic upgrade head`
- mo FastAPI o cong `8000`

Compose noi backend truc tiep vao service `qdrant` qua `http://qdrant:6333`. Neu chay backend local tren may host thi co the giu `QDRANT_URL=http://localhost:6333`.
Trong Docker Compose, backend goi Ollama qua `http://ollama:11434`.

## CRUD API

Tat ca endpoint CRUD nam duoi prefix `/api`.

- `GET/POST /api/users`
- `GET/PATCH/DELETE /api/users/{item_id}`
- `GET/POST /api/refresh-tokens`
- `GET/PATCH/DELETE /api/refresh-tokens/{item_id}`
- `GET/POST /api/documents`
- `GET/PATCH/DELETE /api/documents/{item_id}`
- `POST /api/documents/upload`
- `POST /api/documents/{document_id}/ingest`
- `GET/POST /api/document-contents`
- `GET/PATCH/DELETE /api/document-contents/{item_id}`
- `GET/POST /api/document-chunks`
- `GET/PATCH/DELETE /api/document-chunks/{item_id}`
- `GET /api/rag/config`
- `POST /api/rag/chat`
- `POST /api/rag/reindex`
- `GET/POST /api/chat-sessions`
- `GET/PATCH/DELETE /api/chat-sessions/{item_id}`
- `GET/POST /api/chat-messages`
- `GET/PATCH/DELETE /api/chat-messages/{item_id}`
- `GET/POST /api/message-sources`
- `GET/PATCH/DELETE /api/message-sources/{item_id}`

Ghi chu:

- `POST /api/users` nhan `password` va backend se hash thanh `password_hash`.
- `POST /api/refresh-tokens` nhan `token_value` va backend se hash thanh `token_hash`.
- `POST /api/documents/upload` nhan file PDF `multipart/form-data`, upload len MinIO, extract text bang `pypdf`, chunk text, roi tao/cap nhat `documents`, `document_contents`, `document_chunks`.
- Sau khi chunk xong, backend tao embedding bang `sentence-transformers/all-MiniLM-L6-v2` qua `LangChain HuggingFaceEmbeddings` va upsert vao `Qdrant` collection `document_chunks`.
- `POST /api/documents/{document_id}/ingest` cho phep chay lai buoc extract + chunk + embedding cho tai lieu da upload.
- `POST /api/rag/chat` dung 1 pipeline RAG nhe: `LangChain basic + Qdrant + all-MiniLM-L6-v2`.
- `POST /api/rag/reindex` rebuild toan bo vector trong Qdrant theo payload LangChain hien tai. Nen chay 1 lan neu da co vector cu.
- Danh sach endpoint ho tro `skip` va `limit`.

## Bien moi truong

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
```

Mac dinh backend se goi Ollama voi model `qwen2.5:7b-instruct`, tuong ung voi `Qwen/Qwen2.5-7B-Instruct`.
Neu chay bang Docker Compose, pull model vao container:

```bash
docker exec -it pdf-chatbot-ollama ollama pull qwen2.5:7b-instruct
```

Neu khong dung Docker cho Ollama, pull tren host:

```bash
ollama pull qwen2.5:7b-instruct
```
