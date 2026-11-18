from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database.models import Dataset


class DatasetRepository:
    """CRUD operations for datasets, metadata, and data retention policies."""

    @staticmethod
    def get_by_id(db: Session, dataset_id: str) -> Optional[Dataset]:
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()

    @staticmethod
    def get_for_user(db: Session, dataset_id: str, user_id: str) -> Optional[Dataset]:
        """Return a dataset only when it belongs to the supplied tenant."""
        return (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id, Dataset.user_id == user_id)
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        name: str,
        filename: str,
        user_id: Optional[str] = None,
        total_records: int = 0,
        valid_records: int = 0,
        invalid_records: int = 0,
        duplicate_records: int = 0
    ) -> Dataset:
        dataset = Dataset(
            name=name,
            filename=filename,
            user_id=user_id,
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            duplicate_records=duplicate_records
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def list_datasets(
        db: Session,
        user_id: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dataset], int]:
        query = db.query(Dataset)
        if user_id:
            query = query.filter(Dataset.user_id == user_id)
        if not include_deleted:
            query = query.filter(Dataset.is_deleted == False)

        total = query.count()
        datasets = query.order_by(Dataset.created_at.desc()).offset(offset).limit(limit).all()
        return datasets, total

    @staticmethod
    def soft_delete(db: Session, dataset_id: str, user_id: Optional[str] = None) -> bool:
        """Mark dataset as deleted according to retention policies without immediately dropping data."""
        query = db.query(Dataset).filter(Dataset.id == dataset_id)
        if user_id is not None:
            query = query.filter(Dataset.user_id == user_id)
        dataset = query.first()
        if dataset:
            dataset.is_deleted = True
            dataset.deleted_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @staticmethod
    def purge_expired(db: Session, retention_days: int) -> int:
        """Permanently remove datasets only after the configured retention window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        expired = (
            db.query(Dataset)
            .filter(Dataset.is_deleted == True, Dataset.deleted_at.isnot(None), Dataset.deleted_at < cutoff)
            .all()
        )
        for dataset in expired:
            db.delete(dataset)
        db.commit()
        return len(expired)

    @staticmethod
    def hard_delete(db: Session, dataset_id: str, user_id: Optional[str] = None) -> bool:
        """Permanently delete a dataset and cascade delete all associated customers and predictions."""
        query = db.query(Dataset).filter(Dataset.id == dataset_id)
        if user_id is not None:
            query = query.filter(Dataset.user_id == user_id)
        dataset = query.first()
        if dataset:
            db.delete(dataset)
            db.commit()
            return True
        return False
