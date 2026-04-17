"""allow multiple notebooks per user

Revision ID: 20260416_0005
Revises: 20260416_0004
Create Date: 2026-04-16 04:30:00.000000
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260416_0005"
down_revision = "20260416_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_notebooks_user_id", "notebooks", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_notebooks_user_id",
        "notebooks",
        ["user_id"],
    )
