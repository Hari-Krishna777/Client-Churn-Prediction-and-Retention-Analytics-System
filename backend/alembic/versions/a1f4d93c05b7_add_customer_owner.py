"""add direct customer ownership for tenant isolation

Revision ID: a1f4d93c05b7
Revises: cc457c4a0cbf
"""
from alembic import op
import sqlalchemy as sa

revision = "a1f4d93c05b7"
down_revision = "cc457c4a0cbf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("user_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_customers_user_id_users", "customers", "users", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_customers_user_id", "customers", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_customers_user_id", table_name="customers")
    op.drop_constraint("fk_customers_user_id_users", "customers", type_="foreignkey")
    op.drop_column("customers", "user_id")
