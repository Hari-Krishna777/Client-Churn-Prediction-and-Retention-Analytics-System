import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.customer import CustomerInput, PredictionResponse
from app.schemas.recommendations import CustomerRecommendationResponse
from app.services.feature_engineering import engineer_features
from app.services.model_service import model, threshold, get_risk_category
from app.services.shap_service import ShapService
from app.services.explanation_service import ExplanationService
from app.services.recommendation_service import (
    RecommendationService,
    assign_action_urgency
)
from app.database.connection import get_db
from app.database.models import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.security_service import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict customer churn probability with optional SHAP explanations and recommendations"
)
def predict_customer(
    customer: CustomerInput,
    explain: bool = Query(default=False, description="Include SHAP factors and retention recommendations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer_dict = customer.model_dump()
    customer_id = customer_dict.pop("customer_id", None) or "SINGLE-PREDICTION"

    customer_data = pd.DataFrame([customer_dict])
    processed_data = engineer_features(customer_data)

    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        processed_data = processed_data[expected_features]

    churn_probability = float(model.predict_proba(processed_data)[0][1])
    churn_prediction = "Yes" if churn_probability >= threshold else "No"
    risk_category = get_risk_category(churn_probability)
    action_urgency = assign_action_urgency(risk_category)

    top_churn_factors = None
    top_protective_factors = None
    recommendations = None
    explanation_dicts = []

    if explain:
        shap_df = ShapService.calculate_shap_matrix(processed_data)
        shap_row = shap_df.iloc[0]

        explanation = ExplanationService.explain_customer(
            customer_id=customer_id,
            churn_probability=churn_probability,
            shap_row=shap_row,
            top_n=3
        )
        top_churn_factors = explanation.top_churn_factors
        top_protective_factors = explanation.top_protective_factors

        drivers = ExplanationService.get_top_churn_drivers(shap_row, top_n=5)
        for d in drivers:
            explanation_dicts.append({
                "feature_name": d["feature"],
                "feature_label": d["label"],
                "contribution": d["contribution"],
                "direction": d["direction"]
            })

        recommendations = RecommendationService.generate_customer_recommendations(
            customer_id=customer_id,
            customer_data=customer_dict,
            churn_probability=churn_probability,
            risk_category=risk_category,
            shap_row=shap_row
        )

    # Persist prediction to database
    try:
        cust = CustomerRepository.get_by_customer_id(db, customer_id, user_id=current_user.id)
        if not cust:
            cust = CustomerRepository.create(
                db, customer_id=customer_id, customer_dict=customer_dict, user_id=current_user.id
            )

        pred = PredictionRepository.create(
            db=db,
            customer_id=cust.id,
            churn_probability=churn_probability,
            churn_prediction=churn_prediction,
            risk_category=risk_category,
            action_urgency=action_urgency,
            threshold=threshold,
            tenure_group=str(customer_data.get("TenureGroup", [""])[0]) if "TenureGroup" in customer_data else None,
            avg_monthly_spend=float(customer_data.get("AvgMonthlySpend", [0.0])[0]) if "AvgMonthlySpend" in customer_data else None,
            service_count=int(customer_data.get("ServiceCount", [0])[0]) if "ServiceCount" in customer_data else None,
            explanations=explanation_dicts if explain else None
        )

        if recommendations:
            for r in recommendations:
                RecommendationRepository.create(
                    db=db,
                    prediction_id=pred.id,
                    customer_id=cust.id,
                    recommendation_reason=r.recommendation_reason,
                    suggested_action=r.suggested_action,
                    priority=r.priority,
                    action_urgency=r.action_urgency,
                    supporting_shap_contribution=r.supporting_shap_contribution,
                    shap_feature=r.shap_feature
                )
    except Exception as exc:
        # Do not report a successful prediction that was not recorded.  The
        # caller can retry safely and the error remains visible to operators.
        db.rollback()
        logger.exception("Failed to persist prediction")
        raise HTTPException(status_code=503, detail="Prediction could not be persisted.") from exc

    return PredictionResponse(
        customer_id=customer_id,
        churn_probability=round(churn_probability, 4),
        churn_prediction=churn_prediction,
        risk_category=risk_category,
        threshold=threshold,
        action_urgency=action_urgency if explain else None,
        top_churn_factors=top_churn_factors,
        top_protective_factors=top_protective_factors,
        recommendations=recommendations
    )


@router.get(
    "/predict/history/{customer_id}",
    summary="Retrieve temporal churn prediction history for a customer"
)
def get_customer_prediction_history(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical prediction snapshots and retention actions over time."""
    cust = CustomerRepository.get_by_customer_id(
        db, customer_id, user_id=None if current_user.role == "admin" else current_user.id
    )
    if not cust:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found in database.")

    history = PredictionRepository.get_customer_prediction_history(db, cust.id)
    return {
        "customer_id": customer_id,
        "total_historical_predictions": len(history),
        "history": [
            {
                "prediction_id": p.id,
                "churn_probability": p.churn_probability,
                "churn_prediction": p.churn_prediction,
                "risk_category": p.risk_category,
                "action_urgency": p.action_urgency,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "recommendations_count": len(p.recommendations)
            }
            for p in history
        ]
    }


@router.post(
    "/predict/recommendations",
    response_model=CustomerRecommendationResponse,
    summary="Get dedicated retention recommendations with SHAP support for a customer"
)
def get_customer_retention_recommendations(
    customer: CustomerInput,
    current_user: User = Depends(get_current_user),
):
    """Generate prioritized retention strategies and urgency for a single customer."""
    customer_dict = customer.model_dump()
    customer_id = customer_dict.pop("customer_id", None)

    customer_data = pd.DataFrame([customer_dict])
    processed_data = engineer_features(customer_data)

    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        processed_data = processed_data[expected_features]

    churn_probability = float(model.predict_proba(processed_data)[0][1])
    shap_df = ShapService.calculate_shap_matrix(processed_data)
    shap_row = shap_df.iloc[0]

    return RecommendationService.build_recommendation_response(
        customer_id=customer_id,
        customer_data=customer_dict,
        churn_probability=churn_probability,
        shap_row=shap_row
    )
