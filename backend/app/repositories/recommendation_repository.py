from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import Recommendation


class RecommendationRepository:
    """CRUD operations for retention recommendations."""

    @staticmethod
    def get_by_id(db: Session, recommendation_id: str) -> Optional[Recommendation]:
        return db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()

    @staticmethod
    def create(
        db: Session,
        prediction_id: str,
        customer_id: str,
        recommendation_reason: str,
        suggested_action: str,
        priority: str,
        action_urgency: str,
        supporting_shap_contribution: Optional[float] = None,
        shap_feature: Optional[str] = None,
        commit: bool = True,
    ) -> Recommendation:
        rec = Recommendation(
            prediction_id=prediction_id,
            customer_id=customer_id,
            recommendation_reason=recommendation_reason,
            suggested_action=suggested_action,
            priority=priority,
            action_urgency=action_urgency,
            supporting_shap_contribution=supporting_shap_contribution,
            shap_feature=shap_feature
        )
        db.add(rec)
        if commit:
            db.commit()
            db.refresh(rec)
        else:
            db.flush()
        return rec

    @staticmethod
    def get_for_prediction(db: Session, prediction_id: str) -> List[Recommendation]:
        return (
            db.query(Recommendation)
            .filter(Recommendation.prediction_id == prediction_id)
            .all()
        )

    @staticmethod
    def get_for_customer(db: Session, customer_id: str) -> List[Recommendation]:
        return (
            db.query(Recommendation)
            .filter(Recommendation.customer_id == customer_id)
            .order_by(Recommendation.created_at.desc())
            .all()
        )
