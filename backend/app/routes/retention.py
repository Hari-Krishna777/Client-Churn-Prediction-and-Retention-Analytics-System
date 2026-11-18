import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.database.connection import get_db
from app.database.models import Recommendation, Customer, Prediction, User
from app.services.security_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retention", tags=["Retention Management"])


class UpdateStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_is_allowed(cls, value: str) -> str:
        allowed = {"Pending", "In Progress", "Contacted", "Retained", "Escalated", "Closed"}
        if value not in allowed:
            raise ValueError("Invalid retention status.")
        return value

    @field_validator("notes")
    @classmethod
    def notes_are_bounded(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 2000:
            raise ValueError("Notes must not exceed 2000 characters.")
        return value


@router.get("/actions", summary="Retrieve all retention recommendations with customer context")
def list_retention_actions(
    status: Optional[str] = Query(default=None, description="Filter by status (Pending, In Progress, Contacted, Retained, Escalated, Closed)"),
    priority: Optional[str] = Query(default=None, description="Filter by priority (High, Medium, Low)"),
    urgency: Optional[str] = Query(default=None, description="Filter by urgency (URGENT, PLANNED, MONITOR)"),
    search: Optional[str] = Query(default=None, description="Search by customer ID or action"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Recommendation)
        .options(
            joinedload(Recommendation.customer),
            joinedload(Recommendation.prediction)
        )
    )
    if current_user.role != "admin":
        query = query.join(Customer, Recommendation.customer_id == Customer.id).filter(Customer.user_id == current_user.id)

    if status:
        query = query.filter(Recommendation.status == status)

    if priority:
        query = query.filter(Recommendation.priority.ilike(priority))

    if urgency:
        query = query.filter(Recommendation.action_urgency.ilike(urgency))

    if search:
        query = query.join(Customer, Recommendation.customer_id == Customer.id).filter(
            or_(
                Customer.customer_id.ilike(f"%{search}%"),
                Recommendation.recommendation_reason.ilike(f"%{search}%"),
                Recommendation.suggested_action.ilike(f"%{search}%")
            )
        )

    total = query.count()
    recs = query.order_by(desc(Recommendation.created_at)).offset(offset).limit(limit).all()

    items = []
    for r in recs:
        cust = r.customer
        pred = r.prediction
        items.append({
            "id": r.id,
            "prediction_id": r.prediction_id,
            "customer_id": cust.customer_id if cust else "UNKNOWN",
            "customer_uuid": r.customer_id,
            "tenure": cust.tenure if cust else 0,
            "contract": cust.contract if cust else "Unknown",
            "monthly_charges": cust.monthly_charges if cust else 0.0,
            "churn_probability": pred.churn_probability if pred else 0.0,
            "risk_category": pred.risk_category if pred else "UNKNOWN",
            "recommendation_reason": r.recommendation_reason,
            "suggested_action": r.suggested_action,
            "priority": r.priority,
            "action_urgency": r.action_urgency,
            "supporting_shap_contribution": r.supporting_shap_contribution,
            "shap_feature": r.shap_feature,
            "status": r.status or "Pending",
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "actions": items
    }


@router.patch("/{recommendation_id}/status", summary="Update customer retention follow-up status")
def update_action_status(
    recommendation_id: str,
    payload: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Recommendation).join(Customer, Recommendation.customer_id == Customer.id).filter(Recommendation.id == recommendation_id)
    if current_user.role != "admin":
        query = query.filter(Customer.user_id == current_user.id)
    rec = query.first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    rec.status = payload.status
    if payload.notes is not None:
        rec.notes = payload.notes

    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id,
        "status": rec.status,
        "notes": rec.notes,
        "message": "Retention action status updated successfully"
    }


@router.get("/stats", summary="Retention performance and follow-up metrics")
def get_retention_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Recommendation).join(Customer, Recommendation.customer_id == Customer.id)
    if current_user.role != "admin":
        query = query.filter(Customer.user_id == current_user.id)
    all_recs = query.all()
    total = len(all_recs)

    status_counts = {
        "Pending": 0,
        "In Progress": 0,
        "Contacted": 0,
        "Retained": 0,
        "Escalated": 0,
        "Closed": 0
    }
    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    urgency_counts = {"URGENT": 0, "PLANNED": 0, "MONITOR": 0}

    for r in all_recs:
        st = r.status or "Pending"
        status_counts[st] = status_counts.get(st, 0) + 1

        prio = (r.priority or "Medium").capitalize()
        priority_counts[prio] = priority_counts.get(prio, 0) + 1

        urg = (r.action_urgency or "PLANNED").upper()
        urgency_counts[urg] = urgency_counts.get(urg, 0) + 1

    actioned = status_counts.get("Contacted", 0) + status_counts.get("Retained", 0) + status_counts.get("Closed", 0)
    retained = status_counts.get("Retained", 0)
    success_rate = round((retained / actioned * 100), 1) if actioned > 0 else 0.0

    return {
        "total_actions": total,
        "status_breakdown": status_counts,
        "priority_breakdown": priority_counts,
        "urgency_breakdown": urgency_counts,
        "actioned_count": actioned,
        "retained_count": retained,
        "retention_success_rate": success_rate
    }
