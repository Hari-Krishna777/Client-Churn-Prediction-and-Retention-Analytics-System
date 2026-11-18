from typing import Optional, List
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.database.connection import get_db
from app.database.models import Customer, Prediction, Recommendation, PredictionExplanation
from app.database.models import User
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.feature_engineering import engineer_features
from app.services.model_service import model, threshold, get_risk_category
from app.services.shap_service import ShapService
from app.services.explanation_service import ExplanationService
from app.services.recommendation_service import RecommendationService, assign_action_urgency
from app.services.security_service import get_current_user, verify_dataset_tenant_access
from app.config import DATASET_RETENTION_DAYS

router = APIRouter(tags=["Datasets & Customer Repository"])


@router.post("/datasets/retention/purge", summary="Purge datasets whose retention window has expired")
def purge_expired_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators may run retention purges.")
    count = DatasetRepository.purge_expired(db, DATASET_RETENTION_DAYS)
    return {"purged_datasets": count, "retention_days": DATASET_RETENTION_DAYS}


@router.get(
    "/datasets",
    summary="List uploaded datasets with user isolation"
)
def list_datasets(
    user_id: Optional[str] = Query(default=None, description="Admin-only tenant filter"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted datasets"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scoped_user_id = user_id if current_user.role == "admin" and user_id else (None if current_user.role == "admin" else current_user.id)
    datasets, total = DatasetRepository.list_datasets(
        db, user_id=scoped_user_id, include_deleted=include_deleted, limit=limit, offset=offset
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "filename": d.filename,
                "total_records": d.total_records,
                "valid_records": d.valid_records,
                "invalid_records": d.invalid_records,
                "duplicate_records": d.duplicate_records,
                "is_deleted": d.is_deleted,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in datasets
        ]
    }


@router.get(
    "/datasets/{dataset_id}",
    summary="Get dataset details"
)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = DatasetRepository.get_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    verify_dataset_tenant_access(dataset, current_user)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "filename": dataset.filename,
        "total_records": dataset.total_records,
        "valid_records": dataset.valid_records,
        "invalid_records": dataset.invalid_records,
        "duplicate_records": dataset.duplicate_records,
        "is_deleted": dataset.is_deleted,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None
    }


@router.delete(
    "/datasets/{dataset_id}",
    summary="Delete dataset (supports soft delete retention policy or permanent purge)"
)
def delete_dataset(
    dataset_id: str,
    permanent: bool = Query(default=False, description="Permanently purge dataset instead of soft-delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = DatasetRepository.get_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    verify_dataset_tenant_access(dataset, current_user)
    if permanent and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators may permanently purge datasets.")
    user_id = None if current_user.role == "admin" else current_user.id
    if permanent:
        success = DatasetRepository.hard_delete(db, dataset_id, user_id=user_id)
    else:
        success = DatasetRepository.soft_delete(db, dataset_id, user_id=user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return {"message": f"Dataset {dataset_id} successfully {'purged' if permanent else 'marked deleted'}."}


@router.get(
    "/customers",
    summary="Search, filter, and paginate customers stored in database"
)
def list_customers(
    search: Optional[str] = Query(default=None, description="Search by customer ID, contract, or payment"),
    dataset_id: Optional[str] = Query(default=None, description="Filter by dataset"),
    contract: Optional[str] = Query(default=None, description="Filter by contract type"),
    internet_service: Optional[str] = Query(default=None, description="Filter by internet service"),
    risk_category: Optional[str] = Query(default=None, description="Filter by risk category (LOW, MEDIUM, HIGH)"),
    sort_by: Optional[str] = Query(default=None, description="Sort criteria: probability_desc, probability_asc, tenure_desc, charges_desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Customer)
        .options(
            joinedload(Customer.predictions)
        )
    )

    if dataset_id:
        dataset = DatasetRepository.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        verify_dataset_tenant_access(dataset, current_user)
        query = query.filter(Customer.dataset_id == dataset_id)

    if current_user.role != "admin":
        query = query.filter(Customer.user_id == current_user.id)

    if search:
        query = query.filter(
            or_(
                Customer.customer_id.ilike(f"%{search}%"),
                Customer.contract.ilike(f"%{search}%"),
                Customer.payment_method.ilike(f"%{search}%")
            )
        )

    if contract:
        query = query.filter(Customer.contract == contract)

    if internet_service:
        query = query.filter(Customer.internet_service == internet_service)

    customers_all = query.all()

    # Enrich with latest prediction
    enriched = []
    for c in customers_all:
        latest_pred = c.predictions[-1] if c.predictions else None
        prob = round(latest_pred.churn_probability, 4) if latest_pred else 0.0
        pred_label = latest_pred.churn_prediction if latest_pred else "No"
        risk = latest_pred.risk_category if latest_pred else "LOW"
        urgency = latest_pred.action_urgency if latest_pred else "MONITOR"

        if risk_category and risk.upper() != risk_category.upper():
            continue

        enriched.append({
            "id": c.id,
            "customer_id": c.customer_id,
            "dataset_id": c.dataset_id,
            "gender": c.gender,
            "senior_citizen": c.senior_citizen,
            "partner": c.partner,
            "dependents": c.dependents,
            "tenure": c.tenure,
            "phone_service": c.phone_service,
            "multiple_lines": c.multiple_lines,
            "internet_service": c.internet_service,
            "online_security": c.online_security,
            "online_backup": c.online_backup,
            "device_protection": c.device_protection,
            "tech_support": c.tech_support,
            "streaming_tv": c.streaming_tv,
            "streaming_movies": c.streaming_movies,
            "contract": c.contract,
            "paperless_billing": c.paperless_billing,
            "payment_method": c.payment_method,
            "monthly_charges": c.monthly_charges,
            "total_charges": c.total_charges,
            "churn_probability": prob,
            "churn_prediction": pred_label,
            "risk_category": risk,
            "action_urgency": urgency,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    # Sort if requested
    if sort_by == "probability_desc":
        enriched.sort(key=lambda x: x["churn_probability"], reverse=True)
    elif sort_by == "probability_asc":
        enriched.sort(key=lambda x: x["churn_probability"])
    elif sort_by == "tenure_desc":
        enriched.sort(key=lambda x: x["tenure"], reverse=True)
    elif sort_by == "charges_desc":
        enriched.sort(key=lambda x: x["monthly_charges"], reverse=True)
    else:
        enriched.sort(key=lambda x: x["churn_probability"], reverse=True)

    total = len(enriched)
    paged = enriched[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "customers": paged
    }


@router.get(
    "/customers/{customer_id}",
    summary="Retrieve full customer profile, SHAP explanations, recommendations, and history"
)
def get_customer_details(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve individual customer details with rich SHAP explanations and retention actions."""
    cust = (
        db.query(Customer)
        .options(
            joinedload(Customer.predictions).joinedload(Prediction.explanations),
            joinedload(Customer.predictions).joinedload(Prediction.recommendations),
            joinedload(Customer.recommendations)
        )
        .filter(or_(Customer.customer_id == customer_id, Customer.id == customer_id))
    )
    if current_user.role != "admin":
        cust = cust.filter(Customer.user_id == current_user.id)
    cust = cust.first()

    if not cust:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found."
        )

    # Base customer attributes
    cust_dict = {
        "gender": cust.gender or "Male",
        "SeniorCitizen": cust.senior_citizen or 0,
        "Partner": cust.partner or "No",
        "Dependents": cust.dependents or "No",
        "tenure": cust.tenure or 0,
        "PhoneService": cust.phone_service or "Yes",
        "MultipleLines": cust.multiple_lines or "No",
        "InternetService": cust.internet_service or "DSL",
        "OnlineSecurity": cust.online_security or "No",
        "OnlineBackup": cust.online_backup or "No",
        "DeviceProtection": cust.device_protection or "No",
        "TechSupport": cust.tech_support or "No",
        "StreamingTV": cust.streaming_tv or "No",
        "StreamingMovies": cust.streaming_movies or "No",
        "Contract": cust.contract or "Month-to-month",
        "PaperlessBilling": cust.paperless_billing or "Yes",
        "PaymentMethod": cust.payment_method or "Electronic check",
        "MonthlyCharges": float(cust.monthly_charges or 0.0),
        "TotalCharges": float(cust.total_charges or 0.0)
    }

    # Latest prediction
    latest_pred = cust.predictions[-1] if cust.predictions else None
    shap_factors = []
    top_churn_factors = []
    top_protective_factors = []
    recommendation_items = []

    # If predictions exist and have explanations
    if latest_pred and latest_pred.explanations:
        for exp in latest_pred.explanations:
            item = {
                "feature_name": exp.feature_name,
                "feature_label": exp.feature_label,
                "contribution": exp.contribution,
                "direction": exp.direction,
                "rank": exp.rank
            }
            shap_factors.append(item)
            if exp.direction == "increases_churn":
                top_churn_factors.append(exp.feature_label)
            else:
                top_protective_factors.append(exp.feature_label)

    # If no explanations recorded or no prediction yet, calculate with SHAP service dynamically!
    if not shap_factors:
        try:
            df = pd.DataFrame([cust_dict])
            processed = engineer_features(df)
            expected_feats = getattr(model, "feature_names_in_", None)
            if expected_feats is not None:
                processed = processed[expected_feats]

            calc_prob = float(model.predict_proba(processed)[0][1])
            shap_df = ShapService.calculate_shap_matrix(processed)
            shap_row = shap_df.iloc[0]

            expl = ExplanationService.explain_customer(
                customer_id=cust.customer_id,
                churn_probability=calc_prob,
                shap_row=shap_row,
                top_n=5
            )
            top_churn_factors = expl.top_churn_factors
            top_protective_factors = expl.top_protective_factors

            drivers = ExplanationService.get_top_churn_drivers(shap_row, top_n=10)
            for idx, d in enumerate(drivers):
                shap_factors.append({
                    "feature_name": d["feature"],
                    "feature_label": d["label"],
                    "contribution": d["contribution"],
                    "direction": d["direction"],
                    "rank": idx + 1
                })
        except Exception as e:
            pass

    # Gather recommendations
    if latest_pred and latest_pred.recommendations:
        for r in latest_pred.recommendations:
            recommendation_items.append({
                "id": r.id,
                "recommendation_reason": r.recommendation_reason,
                "suggested_action": r.suggested_action,
                "priority": r.priority,
                "action_urgency": r.action_urgency,
                "supporting_shap_contribution": r.supporting_shap_contribution,
                "shap_feature": r.shap_feature,
                "status": r.status or "Pending",
                "notes": r.notes
            })
    elif cust.recommendations:
        for r in cust.recommendations:
            recommendation_items.append({
                "id": r.id,
                "recommendation_reason": r.recommendation_reason,
                "suggested_action": r.suggested_action,
                "priority": r.priority,
                "action_urgency": r.action_urgency,
                "supporting_shap_contribution": r.supporting_shap_contribution,
                "shap_feature": r.shap_feature,
                "status": r.status or "Pending",
                "notes": r.notes
            })
    else:
        # Generate dynamically
        prob = latest_pred.churn_probability if latest_pred else 0.5
        risk = latest_pred.risk_category if latest_pred else get_risk_category(prob)
        recs = RecommendationService.generate_customer_recommendations(
            customer_id=cust.customer_id,
            customer_data=cust_dict,
            churn_probability=prob,
            risk_category=risk
        )
        for r in recs:
            recommendation_items.append({
                "id": f"rec_{cust.id}_{uuid.uuid4().hex[:6]}" if "uuid" in globals() else "rec_gen",
                "recommendation_reason": r.recommendation_reason,
                "suggested_action": r.suggested_action,
                "priority": r.priority,
                "action_urgency": r.action_urgency,
                "supporting_shap_contribution": r.supporting_shap_contribution,
                "shap_feature": r.shap_feature,
                "status": "Pending",
                "notes": None
            })

    # Historical predictions list
    history_items = []
    if cust.predictions:
        for p in reversed(cust.predictions):
            history_items.append({
                "prediction_id": p.id,
                "churn_probability": round(p.churn_probability, 4),
                "churn_prediction": p.churn_prediction,
                "risk_category": p.risk_category,
                "action_urgency": p.action_urgency,
                "threshold": p.threshold,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })

    # Fallback probability if no prediction
    curr_prob = latest_pred.churn_probability if latest_pred else 0.0
    curr_prediction = latest_pred.churn_prediction if latest_pred else ("Yes" if curr_prob >= threshold else "No")
    curr_risk = latest_pred.risk_category if latest_pred else get_risk_category(curr_prob)
    curr_urgency = latest_pred.action_urgency if latest_pred else assign_action_urgency(curr_risk)

    return {
        "customer": {
            "id": cust.id,
            "customer_id": cust.customer_id,
            "dataset_id": cust.dataset_id,
            "gender": cust.gender,
            "senior_citizen": cust.senior_citizen,
            "partner": cust.partner,
            "dependents": cust.dependents,
            "tenure": cust.tenure,
            "phone_service": cust.phone_service,
            "multiple_lines": cust.multiple_lines,
            "internet_service": cust.internet_service,
            "online_security": cust.online_security,
            "online_backup": cust.online_backup,
            "device_protection": cust.device_protection,
            "tech_support": cust.tech_support,
            "streaming_tv": cust.streaming_tv,
            "streaming_movies": cust.streaming_movies,
            "contract": cust.contract,
            "paperless_billing": cust.paperless_billing,
            "payment_method": cust.payment_method,
            "monthly_charges": cust.monthly_charges,
            "total_charges": cust.total_charges,
            "created_at": cust.created_at.isoformat() if cust.created_at else None
        },
        "prediction": {
            "churn_probability": round(curr_prob, 4),
            "churn_prediction": curr_prediction,
            "risk_category": curr_risk,
            "action_urgency": curr_urgency,
            "threshold": threshold,
            "top_churn_factors": top_churn_factors[:3],
            "top_protective_factors": top_protective_factors[:3]
        },
        "shap_explanations": shap_factors,
        "recommendations": recommendation_items,
        "history": history_items
    }
