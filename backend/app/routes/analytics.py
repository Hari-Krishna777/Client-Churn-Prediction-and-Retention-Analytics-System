from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status
from app.database.models import User
from app.services.security_service import get_current_user
from app.services.batch_service import BatchService

from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    RiskDistributionResponse,
    ChurnFactorsResponse,
    RecommendationSummaryResponse,
    CustomerSegmentsResponse
)

router = APIRouter(prefix="/analytics", tags=["Retention Analytics"])


def _verify_job_access(job_id: Optional[str], current_user: User) -> None:
    """Only expose analytics for a batch owned by the requesting tenant."""
    if not job_id or current_user.role == "admin":
        return
    job = BatchService.get_job(job_id)
    if not job or not job.user_id or str(job.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this analytics dataset.")


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get customer churn overview, counts, and risk breakdown"
)
def get_analytics_overview(
    job_id: Optional[str] = Query(default=None, description="Optional batch job ID to analyze"),
    current_user: User = Depends(get_current_user),
):
    """Return top-level counts of customers, predicted churners, and risk category counts."""
    _verify_job_access(job_id, current_user)
    return AnalyticsService.get_overview(job_id=job_id, user_id=None if current_user.role == "admin" else current_user.id)


@router.get(
    "/risk-distribution",
    response_model=RiskDistributionResponse,
    summary="Get detailed LOW, MEDIUM, and HIGH risk customer distributions"
)
def get_risk_distribution(
    job_id: Optional[str] = Query(default=None, description="Optional batch job ID to analyze"),
    current_user: User = Depends(get_current_user),
):
    """Return customer counts, percentages, and definitions for each risk tier."""
    _verify_job_access(job_id, current_user)
    return AnalyticsService.get_risk_distribution(job_id=job_id, user_id=None if current_user.role == "admin" else current_user.id)


@router.get(
    "/churn-factors",
    response_model=ChurnFactorsResponse,
    summary="Get influential churn factors and protective retention factors"
)
def get_churn_factors(
    job_id: Optional[str] = Query(default=None, description="Optional batch job ID to analyze"),
    top_n: int = Query(default=5, ge=1, le=20, description="Number of top factors to return"),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate SHAP-derived churn drivers and protective retention factors."""
    _verify_job_access(job_id, current_user)
    return AnalyticsService.get_churn_factors(job_id=job_id, top_n=top_n, user_id=None if current_user.role == "admin" else current_user.id)


@router.get(
    "/recommendations",
    response_model=RecommendationSummaryResponse,
    summary="Get retention recommendation distributions and top suggested actions"
)
def get_recommendations_summary(
    job_id: Optional[str] = Query(default=None, description="Optional batch job ID to analyze"),
    current_user: User = Depends(get_current_user),
):
    """Return distribution of retention recommendations by reason, priority, urgency, and action."""
    _verify_job_access(job_id, current_user)
    return AnalyticsService.get_recommendations_summary(job_id=job_id, user_id=None if current_user.role == "admin" else current_user.id)


@router.get(
    "/segments",
    response_model=CustomerSegmentsResponse,
    summary="Get customer segment churn analysis across dimensions"
)
def get_customer_segments(
    job_id: Optional[str] = Query(default=None, description="Optional batch job ID to analyze"),
    current_user: User = Depends(get_current_user),
):
    """Return segmented churn analytics across contracts, tenure groups, services, and payments."""
    _verify_job_access(job_id, current_user)
    return AnalyticsService.get_segments(job_id=job_id, user_id=None if current_user.role == "admin" else current_user.id)
