from typing import Any
from pydantic import BaseModel, Field


class RecordValidationErrorSchema(BaseModel):
    row_index: int
    customer_id: str | None = None
    reasons: list[str]


class ValidationSummary(BaseModel):
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    successfully_processed: int
    warnings: list[str] = Field(default_factory=list)


class CustomerPredictionItem(BaseModel):
    customer_id: str | None = None
    churn_probability: float
    churn_prediction: str
    risk_category: str
    tenure: int | None = None
    MonthlyCharges: float | None = None
    TotalCharges: float | None = None
    Contract: str | None = None
    TenureGroup: str | None = None
    AvgMonthlySpend: float | None = None
    ServiceCount: int | None = None


class BatchPredictResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    created_at: str
    completed_at: str | None = None
    validation_summary: ValidationSummary
    invalid_records: list[RecordValidationErrorSchema] = Field(default_factory=list)
    total_predictions: int
    risk_distribution: dict[str, int]
    download_url: str


class BatchJobStatusResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    created_at: str
    completed_at: str | None = None
    total_records: int
    successfully_processed: int
    validation_summary: ValidationSummary | None = None
    risk_distribution: dict[str, int] | None = None
    error_message: str | None = None


class BatchJobResultsResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    validation_summary: ValidationSummary
    invalid_records: list[RecordValidationErrorSchema] = Field(default_factory=list)
    total_predictions: int
    limit: int
    offset: int
    predictions: list[CustomerPredictionItem]
