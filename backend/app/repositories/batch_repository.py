from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database.models import BatchJobModel


class BatchRepository:
    """CRUD operations for batch processing jobs in the database."""

    @staticmethod
    def get_by_id(db: Session, job_id: str) -> Optional[BatchJobModel]:
        return db.query(BatchJobModel).filter(BatchJobModel.id == job_id).first()

    @staticmethod
    def create(
        db: Session,
        job_id: str,
        filename: str,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        total_records: int = 0
    ) -> BatchJobModel:
        job = BatchJobModel(
            id=job_id,
            filename=filename,
            dataset_id=dataset_id,
            user_id=user_id,
            total_records=total_records,
            status="PROCESSING"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_completion(
        db: Session,
        job_id: str,
        status: str,
        valid_records: int,
        invalid_records: int,
        duplicate_records: int,
        successfully_processed: int,
        risk_distribution: Optional[Dict[str, Any]] = None,
        csv_file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> Optional[BatchJobModel]:
        job = db.query(BatchJobModel).filter(BatchJobModel.id == job_id).first()
        if job:
            job.status = status
            job.valid_records = valid_records
            job.invalid_records = invalid_records
            job.duplicate_records = duplicate_records
            job.successfully_processed = successfully_processed
            job.risk_distribution = risk_distribution
            job.csv_file_path = csv_file_path
            job.error_message = error_message
            if dataset_id:
                job.dataset_id = dataset_id
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def list_jobs(
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BatchJobModel]:
        query = db.query(BatchJobModel)
        if user_id:
            query = query.filter(BatchJobModel.user_id == user_id)
        return query.order_by(BatchJobModel.created_at.desc()).offset(offset).limit(limit).all()
