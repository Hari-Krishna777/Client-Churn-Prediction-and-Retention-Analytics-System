"""create_initial_churniq_tables

Revision ID: cc457c4a0cbf
Revises: 
Create Date: 2026-11-13 21:05:31.692087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc457c4a0cbf'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the ChurnIQ persistence schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("senior_citizen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partner", sa.String(length=10), nullable=True),
        sa.Column("dependents", sa.String(length=10), nullable=True),
        sa.Column("tenure", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phone_service", sa.String(length=10), nullable=True),
        sa.Column("multiple_lines", sa.String(length=30), nullable=True),
        sa.Column("internet_service", sa.String(length=30), nullable=True),
        sa.Column("online_security", sa.String(length=30), nullable=True),
        sa.Column("online_backup", sa.String(length=30), nullable=True),
        sa.Column("device_protection", sa.String(length=30), nullable=True),
        sa.Column("tech_support", sa.String(length=30), nullable=True),
        sa.Column("streaming_tv", sa.String(length=30), nullable=True),
        sa.Column("streaming_movies", sa.String(length=30), nullable=True),
        sa.Column("contract", sa.String(length=50), nullable=True),
        sa.Column("paperless_billing", sa.String(length=10), nullable=True),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("monthly_charges", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_charges", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_customer_id", "customers", ["customer_id"])
    op.create_index("ix_customers_dataset_id", "customers", ["dataset_id"])
    op.create_index("ix_customer_dataset_customer_id", "customers", ["dataset_id", "customer_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("churn_probability", sa.Float(), nullable=False),
        sa.Column("churn_prediction", sa.String(length=10), nullable=False),
        sa.Column("risk_category", sa.String(length=20), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0.4"),
        sa.Column("action_urgency", sa.String(length=20), nullable=False),
        sa.Column("tenure_group", sa.String(length=50), nullable=True),
        sa.Column("avg_monthly_spend", sa.Float(), nullable=True),
        sa.Column("service_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_customer_id", "predictions", ["customer_id"])
    op.create_index("ix_predictions_dataset_id", "predictions", ["dataset_id"])
    op.create_index("ix_predictions_risk_category", "predictions", ["risk_category"])
    op.create_index("ix_predictions_created_at", "predictions", ["created_at"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prediction_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_reason", sa.String(length=255), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("action_urgency", sa.String(length=20), nullable=False),
        sa.Column("supporting_shap_contribution", sa.Float(), nullable=True),
        sa.Column("shap_feature", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_prediction_id", "recommendations", ["prediction_id"])
    op.create_index("ix_recommendations_customer_id", "recommendations", ["customer_id"])

    op.create_table(
        "prediction_explanations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prediction_id", sa.String(length=36), nullable=False),
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("feature_label", sa.String(length=255), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_explanations_prediction_id", "prediction_explanations", ["prediction_id"])

    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successfully_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_distribution", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("csv_file_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_jobs_dataset_id", "batch_jobs", ["dataset_id"])
    op.create_index("ix_batch_jobs_user_id", "batch_jobs", ["user_id"])
    op.create_index("ix_batch_jobs_status", "batch_jobs", ["status"])


def downgrade() -> None:
    """Remove the ChurnIQ persistence schema in dependency order."""
    op.drop_table("batch_jobs")
    op.drop_table("prediction_explanations")
    op.drop_table("recommendations")
    op.drop_table("predictions")
    op.drop_table("customers")
    op.drop_table("datasets")
    op.drop_table("users")
