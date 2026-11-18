import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from app.config import (
    STORAGE_DIR,
    ALL_MODEL_FEATURES
)
from app.services.validation_service import (
    ValidationService,
    ValidationResult
)
from app.services.feature_engineering import engineer_features
from app.services.model_service import model, threshold, get_risk_category
from app.services.recommendation_service import (
    RecommendationService,
    assign_action_urgency
)
from app.schemas.batch import (
    ValidationSummary,
    RecordValidationErrorSchema,
    CustomerPredictionItem,
    BatchJobStatusResponse,
    BatchJobResultsResponse
)
from app.database.connection import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.batch_repository import BatchRepository
from app.services.security_service import sanitize_csv_cell_value

logger = logging.getLogger(__name__)


class BatchJob:
    """Represents the state and results of a batch prediction job."""

    def __init__(self, job_id: str, filename: str, user_id: Optional[str] = None):
        self.job_id = job_id
        self.filename = filename
        self.user_id = user_id
        self.status = "PENDING"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.validation_result: Optional[ValidationResult] = None
        self.total_records: int = 0
        self.successfully_processed: int = 0
        self.risk_distribution: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        self.error_message: Optional[str] = None
        self.predictions_df: Optional[pd.DataFrame] = None
        self.csv_path: Optional[Path] = None
        self.dataset_id: Optional[str] = None

    def to_status_response(self) -> BatchJobStatusResponse:
        val_summary = None
        if self.validation_result:
            val_summary = ValidationSummary(
                total_records=self.validation_result.total_records,
                valid_records=self.validation_result.valid_records,
                invalid_records=self.validation_result.invalid_records,
                duplicate_records=self.validation_result.duplicate_records,
                successfully_processed=self.validation_result.successfully_processed,
                warnings=self.validation_result.warnings
            )

        return BatchJobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            filename=self.filename,
            created_at=self.created_at,
            completed_at=self.completed_at,
            total_records=self.total_records,
            successfully_processed=self.successfully_processed,
            validation_summary=val_summary,
            risk_distribution=self.risk_distribution if self.status == "COMPLETED" else None,
            error_message=self.error_message
        )


class BatchService:
    """Manages batch prediction workflows, execution, and artifact retrieval."""

    _jobs: Dict[str, BatchJob] = {}

    @classmethod
    def get_job(cls, job_id: str) -> Optional[BatchJob]:
        """Retrieve an in-memory job, or restore from storage/database if available."""
        if job_id in cls._jobs:
            return cls._jobs[job_id]

        csv_path = STORAGE_DIR / f"predictions_{job_id}.csv"
        meta_path = STORAGE_DIR / f"meta_{job_id}.json"

        if csv_path.exists() and meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                job = BatchJob(job_id=job_id, filename=meta.get("filename", "unknown.csv"), user_id=meta.get("user_id"))
                job.status = meta.get("status", "COMPLETED")
                job.created_at = meta.get("created_at", "")
                job.completed_at = meta.get("completed_at")
                job.total_records = meta.get("total_records", 0)
                job.successfully_processed = meta.get("successfully_processed", 0)
                job.risk_distribution = meta.get("risk_distribution", {"LOW": 0, "MEDIUM": 0, "HIGH": 0})
                job.csv_path = csv_path
                job.predictions_df = pd.read_csv(csv_path)

                cls._jobs[job_id] = job
                return job
            except Exception as e:
                logger.error(f"Failed to restore job {job_id} from disk: {e}")

        # Check PostgreSQL
        try:
            with SessionLocal() as db:
                db_job = BatchRepository.get_by_id(db, job_id)
                if db_job and db_job.csv_file_path and Path(db_job.csv_file_path).exists():
                    job = BatchJob(job_id=job_id, filename=db_job.filename, user_id=db_job.user_id)
                    job.status = db_job.status
                    job.created_at = db_job.created_at.isoformat() if db_job.created_at else ""
                    job.completed_at = db_job.completed_at.isoformat() if db_job.completed_at else None
                    job.total_records = db_job.total_records
                    job.successfully_processed = db_job.successfully_processed
                    job.risk_distribution = db_job.risk_distribution or {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
                    job.csv_path = Path(db_job.csv_file_path)
                    job.predictions_df = pd.read_csv(job.csv_path)
                    job.dataset_id = db_job.dataset_id
                    cls._jobs[job_id] = job
                    return job
        except Exception:
            pass

        return None

    @classmethod
    def process_batch(cls, file_content: bytes, filename: str, user_id: Optional[str] = None) -> BatchJob:
        """
        Execute full batch workflow:
        1. Validate CSV format, columns, types, domain values, and identifiers.
        2. Feature engineering (TenureGroup, AvgMonthlySpend, ServiceCount).
        3. Model prediction (churn probability + thresholding).
        4. Risk category assignment (LOW, MEDIUM, HIGH).
        5. Export CSV report and persist job metadata.
        6. Persist to PostgreSQL database (Dataset, Customer, Prediction, Recommendation, BatchJob).
        """
        job_id = str(uuid.uuid4())
        job = BatchJob(job_id=job_id, filename=filename, user_id=user_id)
        cls._jobs[job_id] = job

        job.status = "PROCESSING"

        # Step 1: Data validation
        try:
            val_result = ValidationService.validate_csv(file_content)
        except Exception as e:
            job.status = "FAILED"
            job.error_message = f"Validation failed: {str(e)}"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            return job

        job.validation_result = val_result
        job.total_records = val_result.total_records

        if not val_result.is_valid:
            job.status = "FAILED"
            if val_result.missing_columns:
                job.error_message = f"Missing required columns: {', '.join(val_result.missing_columns)}"
            elif val_result.errors:
                job.error_message = val_result.errors[0].reasons[0]
            else:
                job.error_message = "CSV validation failed: no valid records found"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            return job

        # Step 2: Feature engineering on valid records
        valid_df = val_result.valid_df.copy()
        # Neutralize spreadsheet formulas before any user-supplied field is
        # persisted or included in a downloadable report.
        for column in valid_df.select_dtypes(include=["object", "string"]).columns:
            valid_df[column] = valid_df[column].map(sanitize_csv_cell_value)
        features_df = valid_df.drop(columns=["customer_id"])

        engineered_df = engineer_features(features_df)

        # Step 3: Model prediction
        expected_features = getattr(model, "feature_names_in_", ALL_MODEL_FEATURES)
        aligned_data = engineered_df[expected_features]

        probabilities = model.predict_proba(aligned_data)[:, 1]
        binary_predictions = (probabilities >= threshold).astype(int)

        # Step 4: Risk classification & distribution
        churn_pred_labels = ["Yes" if p == 1 else "No" for p in binary_predictions]
        risk_categories = [get_risk_category(float(prob)) for prob in probabilities]

        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for cat in risk_categories:
            risk_dist[cat] = risk_dist.get(cat, 0) + 1

        job.risk_distribution = risk_dist
        job.successfully_processed = len(valid_df)

        # Step 5: Build final predictions dataframe
        output_df = valid_df.copy()
        output_df["TenureGroup"] = engineered_df["TenureGroup"]
        output_df["AvgMonthlySpend"] = engineered_df["AvgMonthlySpend"].round(2)
        output_df["ServiceCount"] = engineered_df["ServiceCount"]
        output_df["churn_probability"] = [round(float(p), 4) for p in probabilities]
        output_df["churn_prediction"] = churn_pred_labels
        output_df["risk_category"] = risk_categories

        job.predictions_df = output_df

        # Save downloadable CSV and metadata
        csv_path = STORAGE_DIR / f"predictions_{job_id}.csv"
        output_df.to_csv(csv_path, index=False)
        job.csv_path = csv_path

        meta_path = STORAGE_DIR / f"meta_{job_id}.json"
        meta_data = {
            "job_id": job_id,
            "filename": filename,
            "user_id": user_id,
            "status": "COMPLETED",
            "created_at": job.created_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "total_records": job.total_records,
            "successfully_processed": job.successfully_processed,
            "risk_distribution": risk_dist,
            "warnings": val_result.warnings
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        # Step 6: Persist records into PostgreSQL Database
        try:
            with SessionLocal() as db:
                default_user = UserRepository.get_or_create_default_user(db)
                actual_user_id = user_id or default_user.id

                dataset = DatasetRepository.create(
                    db=db,
                    name=filename.replace(".csv", ""),
                    filename=filename,
                    user_id=actual_user_id,
                    total_records=job.total_records,
                    valid_records=val_result.valid_records,
                    invalid_records=val_result.invalid_records,
                    duplicate_records=val_result.duplicate_records
                )
                job.dataset_id = dataset.id

                BatchRepository.create(
                    db=db,
                    job_id=job_id,
                    filename=filename,
                    dataset_id=dataset.id,
                    user_id=actual_user_id,
                    total_records=job.total_records
                )
                BatchRepository.update_completion(
                    db=db,
                    job_id=job_id,
                    status="COMPLETED",
                    valid_records=val_result.valid_records,
                    invalid_records=val_result.invalid_records,
                    duplicate_records=val_result.duplicate_records,
                    successfully_processed=job.successfully_processed,
                    risk_distribution=risk_dist,
                    csv_file_path=str(csv_path),
                    dataset_id=dataset.id
                )

                for idx, row in output_df.iterrows():
                    cust_id_str = str(row.get("customer_id") or f"CUST-{idx}")
                    cust = CustomerRepository.create(
                        db=db,
                        customer_id=cust_id_str,
                        customer_dict=row.to_dict(),
                        dataset_id=dataset.id,
                        user_id=actual_user_id,
                        commit=False,
                    )
                    prob_val = float(row.get("churn_probability", 0.0))
                    pred_str = str(row.get("churn_prediction", "No"))
                    risk_str = str(row.get("risk_category", "LOW"))
                    urgency_str = assign_action_urgency(risk_str)

                    pred = PredictionRepository.create(
                        db=db,
                        customer_id=cust.id,
                        dataset_id=dataset.id,
                        churn_probability=prob_val,
                        churn_prediction=pred_str,
                        risk_category=risk_str,
                        action_urgency=urgency_str,
                        tenure_group=str(row.get("TenureGroup")) if pd.notnull(row.get("TenureGroup")) else None,
                        avg_monthly_spend=float(row.get("AvgMonthlySpend")) if pd.notnull(row.get("AvgMonthlySpend")) else None,
                        service_count=int(row.get("ServiceCount")) if pd.notnull(row.get("ServiceCount")) else None,
                        commit=False,
                    )

                    cust_recs = RecommendationService.generate_customer_recommendations(
                        customer_id=cust_id_str,
                        customer_data=row.to_dict(),
                        churn_probability=prob_val,
                        risk_category=risk_str
                    )
                    for r in cust_recs:
                        RecommendationRepository.create(
                            db=db,
                            prediction_id=pred.id,
                            customer_id=cust.id,
                            recommendation_reason=r.recommendation_reason,
                            suggested_action=r.suggested_action,
                            priority=r.priority,
                            action_urgency=r.action_urgency,
                            supporting_shap_contribution=r.supporting_shap_contribution,
                            shap_feature=r.shap_feature,
                            commit=False,
                        )
                db.commit()
        except Exception as e:
            logger.warning("Database persistence for batch %s encountered an error: %s", job_id, type(e).__name__)

        job.status = "COMPLETED"
        job.completed_at = meta_data["completed_at"]
        return job

    @classmethod
    def get_results(
        cls,
        job_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[BatchJobResultsResponse]:
        """Retrieve paginated results for a completed batch prediction job."""
        job = cls.get_job(job_id)
        if not job or job.predictions_df is None:
            return None

        total_predictions = len(job.predictions_df)
        paged_df = job.predictions_df.iloc[offset : offset + limit]

        prediction_items: list[CustomerPredictionItem] = []
        for _, row in paged_df.iterrows():
            item = CustomerPredictionItem(
                customer_id=row.get("customer_id"),
                churn_probability=float(row.get("churn_probability", 0.0)),
                churn_prediction=str(row.get("churn_prediction", "No")),
                risk_category=str(row.get("risk_category", "LOW")),
                tenure=int(row.get("tenure")) if pd.notnull(row.get("tenure")) else None,
                MonthlyCharges=float(row.get("MonthlyCharges")) if pd.notnull(row.get("MonthlyCharges")) else None,
                TotalCharges=float(row.get("TotalCharges")) if pd.notnull(row.get("TotalCharges")) else None,
                Contract=row.get("Contract"),
                TenureGroup=str(row.get("TenureGroup")) if pd.notnull(row.get("TenureGroup")) else None,
                AvgMonthlySpend=float(row.get("AvgMonthlySpend")) if pd.notnull(row.get("AvgMonthlySpend")) else None,
                ServiceCount=int(row.get("ServiceCount")) if pd.notnull(row.get("ServiceCount")) else None
            )
            prediction_items.append(item)

        invalid_schemas = []
        if job.validation_result and job.validation_result.errors:
            for err in job.validation_result.errors:
                invalid_schemas.append(
                    RecordValidationErrorSchema(
                        row_index=err.row_index,
                        customer_id=err.customer_id,
                        reasons=err.reasons
                    )
                )

        val_summary = ValidationSummary(
            total_records=job.total_records,
            valid_records=job.validation_result.valid_records if job.validation_result else job.successfully_processed,
            invalid_records=job.validation_result.invalid_records if job.validation_result else 0,
            duplicate_records=job.validation_result.duplicate_records if job.validation_result else 0,
            successfully_processed=job.successfully_processed,
            warnings=job.validation_result.warnings if job.validation_result else []
        )

        return BatchJobResultsResponse(
            job_id=job.job_id,
            status=job.status,
            filename=job.filename,
            validation_summary=val_summary,
            invalid_records=invalid_schemas,
            total_predictions=total_predictions,
            limit=limit,
            offset=offset,
            predictions=prediction_items
        )
