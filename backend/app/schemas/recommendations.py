from typing import List, Optional
from pydantic import BaseModel, Field


class RetentionRecommendation(BaseModel):
    customer_id: Optional[str] = None
    churn_probability: float
    risk_category: str
    recommendation_reason: str
    suggested_action: str
    priority: str  # "High", "Medium", "Low"
    action_urgency: str  # "URGENT", "PLANNED", "MONITOR"
    supporting_shap_contribution: Optional[float] = None
    shap_feature: Optional[str] = None


class CustomerRecommendationResponse(BaseModel):
    customer_id: Optional[str] = None
    churn_probability: float
    risk_category: str
    action_urgency: str
    total_recommendations: int
    recommendations: List[RetentionRecommendation] = Field(default_factory=list)
