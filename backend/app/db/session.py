from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401


def get_engine(database_url: str | None = None):
    return create_engine(
        database_url or get_settings().resolved_database_url,
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(
    bind=get_engine(),
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def init_db(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    Base.metadata.create_all(bind=engine)
    _apply_safe_schema_updates(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _apply_safe_schema_updates(engine) -> None:
    """Apply additive PostgreSQL schema fixes without dropping user data."""

    statements = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_verified boolean
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS name varchar(255)
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS full_name varchar(255)
        """,
        """
        UPDATE users
        SET is_verified = true
        WHERE is_verified IS NULL
        """,
        """
        ALTER TABLE users
        ALTER COLUMN is_verified SET DEFAULT false
        """,
        """
        ALTER TABLE users
        ALTER COLUMN is_verified SET NOT NULL
        """,
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS notebook_id uuid
        """,
        """
        ALTER TABLE chat_sessions
        ADD COLUMN IF NOT EXISTS notebook_id uuid
        """,
        """
        ALTER TABLE notebooks
        DROP CONSTRAINT IF EXISTS uq_notebooks_user_id
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_documents_notebook_id
        ON documents (notebook_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_chat_sessions_notebook_id
        ON chat_sessions (notebook_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_notebooks_user_id
        ON notebooks (user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_email_otps_email
        ON email_otps (email)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id
        ON refresh_tokens (user_id)
        """,
        """
        INSERT INTO notebooks (id, user_id, title, metadata, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            users.id,
            CONCAT(COALESCE(NULLIF(split_part(users.email, '@', 1), ''), 'My'), '''s notebook'),
            '{}'::jsonb,
            now(),
            now()
        FROM users
        WHERE NOT EXISTS (
            SELECT 1
            FROM notebooks
            WHERE notebooks.user_id = users.id
        )
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'chat_sessions'
                  AND column_name = 'user_id'
            ) THEN
                EXECUTE '
                    UPDATE chat_sessions
                    SET notebook_id = notebooks.id
                    FROM notebooks
                    WHERE chat_sessions.notebook_id IS NULL
                      AND chat_sessions.user_id = notebooks.user_id
                ';
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_documents_notebook_id_notebooks'
            ) THEN
                ALTER TABLE documents
                ADD CONSTRAINT fk_documents_notebook_id_notebooks
                FOREIGN KEY (notebook_id) REFERENCES notebooks(id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_chat_sessions_notebook_id_notebooks'
            ) THEN
                ALTER TABLE chat_sessions
                ADD CONSTRAINT fk_chat_sessions_notebook_id_notebooks
                FOREIGN KEY (notebook_id) REFERENCES notebooks(id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
