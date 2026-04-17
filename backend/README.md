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
- `notebooks`: moi user co nhieu notebook; notebook gom nhieu PDF va chat session.
- `pending_registrations`: luu tam email va password hash trong luc cho xac thuc OTP dang ky.
- `email_otps`: luu OTP cho `register` va `reset_password`.
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

Auth flow moi:

- `POST /api/auth/register/request`
- `POST /api/auth/register/verify`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password/request`
- `POST /api/auth/forgot-password/verify`
- `GET/POST /api/notebooks`
- `GET/PATCH /api/notebooks/{item_id}`
- `GET /api/documents`
- `GET/PATCH/DELETE /api/documents/{item_id}`
- `POST /api/documents/upload`
- `POST /api/documents/{document_id}/ingest`
- `GET /api/document-contents`
- `GET /api/document-contents/{item_id}`
- `GET /api/document-chunks`
- `GET /api/document-chunks/{item_id}`
- `GET /api/rag/config`
- `POST /api/rag/chat`
- `POST /api/rag/reindex`
- `GET/POST /api/chat-sessions`
- `GET/PATCH/DELETE /api/chat-sessions/{item_id}`

Ghi chu:

- `POST /api/auth/register/request` validate email, password, tao OTP, luu pending registration, roi gui OTP qua SMTP Gmail.
- `POST /api/auth/register/verify` verify OTP va chi tao `users` sau khi ma dung, chua het han, chua dung. Sau khi verify, backend tu tao notebook mac dinh dau tien cho user.
- `POST /api/auth/login` chi cho phep user da verify email dang nhap va tra ve access token + refresh token. Payload `user` trong response gom `email` va `name` duoc suy ra tu email.
- `GET /api/auth/me` tra ve `email` va `name` cua user hien tai duoc suy ra tu access token `Bearer`.
- `POST /api/auth/forgot-password/request` tao OTP reset password cho email ton tai.
- `POST /api/auth/forgot-password/verify` verify OTP reset, hash mat khau moi va revoke refresh token cu.
- `refresh_tokens` duoc xu ly noi bo trong auth service, khong expose CRUD API cong khai.
- `users` la bang noi bo phuc vu auth va lien ket du lieu, khong con expose CRUD API cong khai.
- `GET/POST/PATCH /api/notebooks*` cho phep user liet ke, tao va sua cac notebook cua chinh minh.
- `documents`, `document_contents`, `document_chunks` va `chat_sessions` deu duoc scope theo notebook. User da dang nhap chi thay du lieu trong notebook duoc chon cua minh; request khong auth chi thay du lieu public khong gan notebook.
- Cac endpoint co chon notebook (`documents`, `chat-sessions`, `rag/chat`) deu nhan `notebook_id` tuy chon. Neu bo trong, backend se dung notebook mac dinh cua user cho cac flow can tao du lieu moi.
- `POST /api/documents/upload` nhan file PDF `multipart/form-data`, upload len MinIO, extract text bang `pypdf`, chunk text, roi tao/cap nhat `documents`, `document_contents`, `document_chunks`. Neu co access token thi document se duoc gan vao notebook duoc chon hoac notebook mac dinh.
- Sau khi chunk xong, backend tao embedding bang `sentence-transformers/all-MiniLM-L6-v2` qua `LangChain HuggingFaceEmbeddings` va upsert vao `Qdrant` collection `document_chunks`.
- `POST /api/documents/{document_id}/ingest` cho phep chay lai buoc extract + chunk + embedding cho tai lieu da upload trong scope hien tai.
- `POST /api/rag/chat` dung 1 pipeline RAG nhe: `LangChain basic + Qdrant + all-MiniLM-L6-v2`. Request JSON co the gui `notebook_id`; neu khong gui va cung khong chi ro `document_id`/`session_id`, retrieval mac dinh chi tim trong notebook mac dinh cua user hien tai.
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

Mac dinh backend se goi Ollama voi model `qwen2.5:7b-instruct`, tuong ung voi `Qwen/Qwen2.5-7B-Instruct`.
Neu chay bang Docker Compose, pull model vao container:

```bash
docker exec -it pdf-chatbot-ollama ollama pull qwen2.5:7b-instruct
```

Neu khong dung Docker cho Ollama, pull tren host:

```bash
ollama pull qwen2.5:7b-instruct
```
