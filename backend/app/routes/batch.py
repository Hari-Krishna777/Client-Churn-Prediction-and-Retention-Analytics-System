import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.repositories.batch_repository import BatchRepository
from app.services.batch_service import BatchService
from app.services.security_service import get_current_user, validate_uploaded_csv
from app.schemas.batch import (
    BatchPredictResponse,
    BatchJobStatusResponse,
    BatchJobResultsResponse,
    ValidationSummary,
    RecordValidationErrorSchema
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["Batch Predictions"])


@router.post(
    "/predict",
    response_model=BatchPredictResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload customer CSV and generate batch churn predictions"
)
async def upload_batch_predict(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a customer dataset in CSV format, validate records, generate engineered
    features and model predictions, classify risk categories, and return summary metrics.
    """
    filename = file.filename or "uploaded_customers.csv"

    # 1. Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    if not content or len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty CSV file: file contains 0 bytes."
        )

    # 2. Strict file security validation (extension, size limits, binary execution rejection)
    validate_uploaded_csv(content, filename)

    # 3. Process batch through validation, feature engineering, and inference scoped to tenant
    job = BatchService.process_batch(content, filename, user_id=current_user.id)

    if job.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=job.error_message or "Batch processing failed during data validation."
        )

    # 4. Construct response
    val = job.validation_result
    val_summary = ValidationSummary(
        total_records=val.total_records if val else job.total_records,
        valid_records=val.valid_records if val else job.successfully_processed,
        invalid_records=val.invalid_records if val else 0,
        duplicate_records=val.duplicate_records if val else 0,
        successfully_processed=job.successfully_processed,
        warnings=val.warnings if val else []
    )

    invalid_items = []
    if val and val.errors:
        for err in val.errors:
            invalid_items.append(
                RecordValidationErrorSchema(
                    row_index=err.row_index,
                    customer_id=err.customer_id,
                    reasons=err.reasons
                )
            )

    return BatchPredictResponse(
        job_id=job.job_id,
        status=job.status,
        filename=job.filename,
        created_at=job.created_at,
        completed_at=job.completed_at,
        validation_summary=val_summary,
        invalid_records=invalid_items,
        total_predictions=job.successfully_processed,
        risk_distribution=job.risk_distribution,
        download_url=f"/batch/{job.job_id}/download"
    )


@router.get(
    "/jobs",
    summary="List batch prediction jobs and upload history"
)
def list_batch_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve historical batch prediction jobs with status and metrics."""
    user_scope = None if current_user.role == "admin" else current_user.id
    jobs = BatchRepository.list_jobs(db, user_id=user_scope, limit=limit, offset=offset)
    return [
        {
            "job_id": j.id,
            "filename": j.filename,
            "status": j.status,
            "total_records": j.total_records,
            "valid_records": j.valid_records,
            "invalid_records": j.invalid_records,
            "duplicate_records": j.duplicate_records,
            "successfully_processed": j.successfully_processed,
            "risk_distribution": j.risk_distribution,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "download_url": f"/batch/{j.id}/download"
        }
        for j in jobs
    ]


@router.get(
    "/{job_id}",
    response_model=BatchJobStatusResponse,
    summary="Check batch processing status"
)
def get_batch_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retrieve the current processing status and metadata for a batch job."""
    job = BatchService.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' not found."
        )

    if job.user_id and current_user.role != "admin" and str(job.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to access this batch job."
        )

    return job.to_status_response()


@router.get(
    "/{job_id}/results",
    response_model=BatchJobResultsResponse,
    summary="Retrieve batch prediction results"
)
def get_batch_results(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of prediction records to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user)
):
    """Retrieve paginated customer predictions, risk categories, and validation results."""
    job = BatchService.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' not found."
        )

    if job.user_id and current_user.role != "admin" and str(job.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to access results for this batch job."
        )

    results = BatchService.get_results(job_id, limit=limit, offset=offset)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch job '{job_id}' is in status '{job.status}' and has no results."
        )

    return results


@router.get(
    "/{job_id}/download",
    summary="Download prediction results as CSV"
)
def download_batch_csv(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download the full prediction report as a CSV file."""
    job = BatchService.get_job(job_id)
    if not job or not job.csv_path or not job.csv_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction download file for batch job '{job_id}' not found."
        )

    if job.user_id and current_user.role != "admin" and str(job.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to download this batch report."
        )

    return FileResponse(
        path=str(job.csv_path),
        media_type="text/csv",
        filename=f"churn_predictions_{job_id}.csv"
    )
