"""add notebooks and scope resources

Revision ID: 20260416_0004
Revises: 20260416_0003
Create Date: 2026-04-16 03:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260416_0004"
down_revision = "20260416_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notebooks_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notebooks")),
        sa.UniqueConstraint("user_id", name="uq_notebooks_user_id"),
    )
    op.create_index(op.f("ix_notebooks_user_id"), "notebooks", ["user_id"], unique=False)

    op.execute(
        """
        INSERT INTO notebooks (id, user_id, title, metadata, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            users.id,
            CONCAT(COALESCE(NULLIF(split_part(users.email, '@', 1), ''), 'my'), '''s notebook'),
            '{}'::jsonb,
            now(),
            now()
        FROM users
        WHERE NOT EXISTS (
            SELECT 1
            FROM notebooks
            WHERE notebooks.user_id = users.id
        )
        """
    )

    op.add_column("documents", sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_documents_notebook_id"), "documents", ["notebook_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_documents_notebook_id_notebooks"),
        "documents",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("chat_sessions", sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_chat_sessions_notebook_id"), "chat_sessions", ["notebook_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_chat_sessions_notebook_id_notebooks"),
        "chat_sessions",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE chat_sessions
        SET notebook_id = notebooks.id
        FROM notebooks
        WHERE chat_sessions.user_id = notebooks.user_id
        """
    )

    op.drop_constraint(op.f("fk_chat_sessions_user_id_users"), "chat_sessions", type_="foreignkey")
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "user_id")


def downgrade() -> None:
    op.add_column("chat_sessions", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_chat_sessions_user_id_users"),
        "chat_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE chat_sessions
        SET user_id = notebooks.user_id
        FROM notebooks
        WHERE chat_sessions.notebook_id = notebooks.id
        """
    )

    op.drop_constraint(op.f("fk_chat_sessions_notebook_id_notebooks"), "chat_sessions", type_="foreignkey")
    op.drop_index(op.f("ix_chat_sessions_notebook_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "notebook_id")

    op.drop_constraint(op.f("fk_documents_notebook_id_notebooks"), "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_notebook_id"), table_name="documents")
    op.drop_column("documents", "notebook_id")

    op.drop_index(op.f("ix_notebooks_user_id"), table_name="notebooks")
    op.drop_table("notebooks")
