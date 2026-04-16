"""remove document checksum sha256

Revision ID: 20260416_0002
Revises: 9b4b7e7c2d31
Create Date: 2026-04-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260416_0002"
down_revision = "9b4b7e7c2d31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS uq_documents_checksum_sha256")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS checksum_sha256")


def downgrade() -> None:
    op.add_column("documents", sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
    op.create_unique_constraint(
        "uq_documents_checksum_sha256",
        "documents",
        ["checksum_sha256"],
    )
