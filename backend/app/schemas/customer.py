from typing import Literal, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.recommendations import RetentionRecommendation

YesNo = Literal["Yes", "No"]


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str | None = None

    gender: Literal["Male", "Female"]
    SeniorCitizen: Literal[0, 1]
    Partner: YesNo
    Dependents: YesNo

    tenure: int = Field(ge=0, le=72)

    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]

    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: Literal["Yes", "No", "No internet service"]
    OnlineBackup: Literal["Yes", "No", "No internet service"]
    DeviceProtection: Literal["Yes", "No", "No internet service"]
    TechSupport: Literal["Yes", "No", "No internet service"]
    StreamingTV: Literal["Yes", "No", "No internet service"]
    StreamingMovies: Literal["Yes", "No", "No internet service"]

    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo

    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)"
    ]

    MonthlyCharges: float = Field(ge=0)
    TotalCharges: float = Field(ge=0)


class PredictionResponse(BaseModel):
    customer_id: str | None = None
    churn_probability: float
    churn_prediction: str
    risk_category: str
    threshold: float
    action_urgency: Optional[str] = None
    top_churn_factors: Optional[List[str]] = None
    top_protective_factors: Optional[List[str]] = None
    recommendations: Optional[List[RetentionRecommendation]] = None
