from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AnalyticsOverviewResponse(BaseModel):
    total_customers: int
    predicted_churners: int
    predicted_retained: int
    churn_rate_percentage: float
    average_churn_probability: float
    risk_distribution: Dict[str, int]
    avg_churn_by_risk: Dict[str, float]
    classification_threshold: float
    job_id: Optional[str] = None


class RiskDistributionResponse(BaseModel):
    counts: Dict[str, int]
    percentages: Dict[str, float]
    thresholds: Dict[str, float]
    descriptions: Dict[str, str]
    job_id: Optional[str] = None


class ChurnFactorMetric(BaseModel):
    factor: str
    feature_name: str
    impact_score: float
    affected_customers_count: int
    affected_percentage: float
    direction: str  # "increases_churn" or "decreases_churn"


class ChurnFactorsResponse(BaseModel):
    total_analyzed: int
    top_churn_drivers: List[ChurnFactorMetric]
    top_protective_factors: List[ChurnFactorMetric]
    job_id: Optional[str] = None


class RecommendationSummaryResponse(BaseModel):
    total_recommendations: int
    unique_customers_receiving_recommendations: int
    by_reason: Dict[str, int]
    by_priority: Dict[str, int]
    by_urgency: Dict[str, int]
    top_suggested_actions: List[Dict[str, Any]]
    job_id: Optional[str] = None


class SegmentMetric(BaseModel):
    segment_name: str
    customer_count: int
    churn_count: int
    churn_rate_percentage: float
    avg_churn_probability: float
    dominant_risk_category: str


class CustomerSegmentsResponse(BaseModel):
    by_contract: List[SegmentMetric]
    by_tenure_group: List[SegmentMetric]
    by_internet_service: List[SegmentMetric]
    by_payment_method: List[SegmentMetric]
    highest_risk_segments: List[SegmentMetric]
    job_id: Optional[str] = None
