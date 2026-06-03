from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "pdf-chatbot"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pdf_chatbot"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    database_url: str | None = None
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "document_chunks"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "pdf-documents"
    minio_secure: bool = False
    document_chunk_size: int = 1000
    document_chunk_overlap: int = 200
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    retrieval_top_k: int = 5
    chat_provider: str = "ollama"
    chat_temperature: float = 0.1
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str | None = "llama3"
    google_api_key: str | None = None
    google_model_name: str | None = None
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    otp_expire_minutes: int = 10
    otp_length: int = 6
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_starttls: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
