# Workspace Layout

`docker-compose.yml` va `.env.example` nam o root de dung chung cho infrastructure local.

Backend project nam trong thu muc `backend/`.

```text
demo1/
|-- .env.example
|-- docker-compose.yml
`-- backend/
```

Compose hien tai chay:

- `postgres`
- `backend` FastAPI tai `http://127.0.0.1:8000`
