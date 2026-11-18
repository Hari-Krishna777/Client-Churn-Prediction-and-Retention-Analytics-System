"""add authentication and retention tracking columns

Revision ID: 7d91e3b2a6f4
Revises: a1f4d93c05b7
"""
from alembic import op
import sqlalchemy as sa

revision = "7d91e3b2a6f4"
down_revision = "a1f4d93c05b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))
    op.add_column("datasets", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "recommendations",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Pending"),
    )
    op.add_column("recommendations", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("recommendations", "notes")
    op.drop_column("recommendations", "status")
    op.drop_column("datasets", "deleted_at")
    op.drop_column("users", "hashed_password")
