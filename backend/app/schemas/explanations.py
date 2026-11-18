from typing import List, Optional
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    feature: str
    label: str
    contribution: float
    direction: str  # "increases_churn" or "decreases_churn"


class CustomerExplanation(BaseModel):
    customer_id: Optional[str] = None
    churn_probability: float
    top_churn_factors: List[str] = Field(
        description="Top features pushing prediction towards higher churn"
    )
    top_protective_factors: List[str] = Field(
        default_factory=list,
        description="Top features pushing prediction towards lower churn"
    )
    detailed_contributions: Optional[List[FeatureContribution]] = None
