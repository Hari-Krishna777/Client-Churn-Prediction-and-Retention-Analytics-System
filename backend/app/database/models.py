import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(50), default="analyst", nullable=False)  # admin, analyst, viewer
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    batch_jobs = relationship("BatchJobModel", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    total_records = Column(Integer, default=0, nullable=False)
    valid_records = Column(Integer, default=0, nullable=False)
    invalid_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete & retention policy
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="datasets")
    customers = relationship("Customer", back_populates="dataset", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="dataset", cascade="all, delete-orphan")
    batch_jobs = relationship("BatchJobModel", back_populates="dataset", cascade="all, delete-orphan")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(100), nullable=False, index=True)  # Telco ID (e.g. 7590-VHVEG)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    # Direct ownership also protects single-customer predictions, which do not
    # originate from an uploaded dataset.
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Telco demographic & service fields
    gender = Column(String(20), nullable=True)
    senior_citizen = Column(Integer, default=0, nullable=False)
    partner = Column(String(10), nullable=True)
    dependents = Column(String(10), nullable=True)
    tenure = Column(Integer, default=0, nullable=False)
    phone_service = Column(String(10), nullable=True)
    multiple_lines = Column(String(30), nullable=True)
    internet_service = Column(String(30), nullable=True)
    online_security = Column(String(30), nullable=True)
    online_backup = Column(String(30), nullable=True)
    device_protection = Column(String(30), nullable=True)
    tech_support = Column(String(30), nullable=True)
    streaming_tv = Column(String(30), nullable=True)
    streaming_movies = Column(String(30), nullable=True)
    contract = Column(String(50), nullable=True)
    paperless_billing = Column(String(10), nullable=True)
    payment_method = Column(String(100), nullable=True)
    monthly_charges = Column(Float, default=0.0, nullable=False)
    total_charges = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="customers")
    user = relationship("User", foreign_keys=[user_id])
    predictions = relationship("Prediction", back_populates="customer", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_customer_dataset_customer_id", "dataset_id", "customer_id"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)

    churn_probability = Column(Float, nullable=False)
    churn_prediction = Column(String(10), nullable=False)  # "Yes", "No"
    risk_category = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH
    threshold = Column(Float, default=0.40, nullable=False)
    action_urgency = Column(String(20), nullable=False)  # URGENT, PLANNED, MONITOR

    # Engineered feature snapshot at time of prediction
    tenure_group = Column(String(50), nullable=True)
    avg_monthly_spend = Column(Float, nullable=True)
    service_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    customer = relationship("Customer", back_populates="predictions")
    dataset = relationship("Dataset", back_populates="predictions")
    recommendations = relationship("Recommendation", back_populates="prediction", cascade="all, delete-orphan")
    explanations = relationship("PredictionExplanation", back_populates="prediction", cascade="all, delete-orphan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prediction_id = Column(String(36), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)

    recommendation_reason = Column(String(255), nullable=False)
    suggested_action = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)  # High, Medium, Low
    action_urgency = Column(String(20), nullable=False)  # URGENT, PLANNED, MONITOR
    supporting_shap_contribution = Column(Float, nullable=True)
    shap_feature = Column(String(100), nullable=True)
    status = Column(String(50), default="Pending", nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    prediction = relationship("Prediction", back_populates="recommendations")
    customer = relationship("Customer", back_populates="recommendations")


class PredictionExplanation(Base):
    __tablename__ = "prediction_explanations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prediction_id = Column(String(36), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True)

    feature_name = Column(String(100), nullable=False)
    feature_label = Column(String(255), nullable=False)
    contribution = Column(Float, nullable=False)
    direction = Column(String(30), nullable=False)  # increases_churn, decreases_churn
    rank = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    prediction = relationship("Prediction", back_populates="explanations")


class BatchJobModel(Base):
    __tablename__ = "batch_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)  # job_id
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    filename = Column(String(255), nullable=False)
    status = Column(String(30), default="PENDING", nullable=False, index=True)
    total_records = Column(Integer, default=0, nullable=False)
    valid_records = Column(Integer, default=0, nullable=False)
    invalid_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)
    successfully_processed = Column(Integer, default=0, nullable=False)
    risk_distribution = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    csv_file_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dataset = relationship("Dataset", back_populates="batch_jobs")
    user = relationship("User", back_populates="batch_jobs")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")
