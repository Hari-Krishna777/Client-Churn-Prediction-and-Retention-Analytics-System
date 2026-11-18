from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.database.models import Prediction, PredictionExplanation


class PredictionRepository:
    """CRUD operations for predictions, SHAP explanations, and prediction history."""

    @staticmethod
    def get_by_id(db: Session, prediction_id: str) -> Optional[Prediction]:
        return (
            db.query(Prediction)
            .options(
                joinedload(Prediction.recommendations),
                joinedload(Prediction.explanations),
                joinedload(Prediction.customer)
            )
            .filter(Prediction.id == prediction_id)
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        customer_id: str,
        churn_probability: float,
        churn_prediction: str,
        risk_category: str,
        action_urgency: str,
        threshold: float = 0.40,
        dataset_id: Optional[str] = None,
        tenure_group: Optional[str] = None,
        avg_monthly_spend: Optional[float] = None,
        service_count: Optional[int] = None,
        explanations: Optional[List[Dict[str, Any]]] = None,
        commit: bool = True,
    ) -> Prediction:
        prediction = Prediction(
            customer_id=customer_id,
            dataset_id=dataset_id,
            churn_probability=churn_probability,
            churn_prediction=churn_prediction,
            risk_category=risk_category,
            threshold=threshold,
            action_urgency=action_urgency,
            tenure_group=tenure_group,
            avg_monthly_spend=avg_monthly_spend,
            service_count=service_count
        )
        db.add(prediction)
        db.flush()

        # Add SHAP explanations if provided
        if explanations:
            for idx, exp in enumerate(explanations):
                expl_obj = PredictionExplanation(
                    prediction_id=prediction.id,
                    feature_name=exp.get("feature_name", ""),
                    feature_label=exp.get("feature_label", ""),
                    contribution=float(exp.get("contribution", 0.0)),
                    direction=exp.get("direction", "increases_churn"),
                    rank=idx + 1
                )
                db.add(expl_obj)

        if commit:
            db.commit()
            db.refresh(prediction)
        else:
            db.flush()
        return prediction

    @staticmethod
    def get_customer_prediction_history(
        db: Session,
        customer_uuid: str,
        limit: int = 50
    ) -> List[Prediction]:
        """Retrieve temporal prediction history for a customer."""
        return (
            db.query(Prediction)
            .options(joinedload(Prediction.recommendations))
            .filter(Prediction.customer_id == customer_uuid)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_predictions(
        db: Session,
        dataset_id: Optional[str] = None,
        risk_category: Optional[str] = None,
        churn_prediction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Prediction], int]:
        query = db.query(Prediction).options(
            joinedload(Prediction.customer),
            joinedload(Prediction.recommendations)
        )

        if dataset_id:
            query = query.filter(Prediction.dataset_id == dataset_id)

        if risk_category:
            query = query.filter(Prediction.risk_category == risk_category)

        if churn_prediction:
            query = query.filter(Prediction.churn_prediction == churn_prediction)

        total = query.count()
        predictions = (
            query.order_by(Prediction.churn_probability.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return predictions, total
