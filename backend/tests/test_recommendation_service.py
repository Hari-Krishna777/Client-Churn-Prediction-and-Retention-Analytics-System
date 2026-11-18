import pytest
import pandas as pd

from app.services.recommendation_service import (
    RecommendationService,
    assign_action_urgency
)


def test_action_urgency_assignment():
    """Confirm urgency strictly matches risk bands: HIGH->URGENT, MEDIUM->PLANNED, LOW->MONITOR."""
    assert assign_action_urgency("HIGH") == "URGENT"
    assert assign_action_urgency("MEDIUM") == "PLANNED"
    assert assign_action_urgency("LOW") == "MONITOR"


def test_recommendations_for_high_risk_customer():
    """Verify retention recommendations generated for high risk customer matching conditions."""
    customer_data = {
        "Contract": "Month-to-month",
        "tenure": 3,
        "OnlineSecurity": "No",
        "TechSupport": "No",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 85.50
    }
    
    recs = RecommendationService.generate_customer_recommendations(
        customer_id="HIGH-001",
        customer_data=customer_data,
        churn_probability=0.88,
        risk_category="HIGH"
    )
    
    reasons = [r.recommendation_reason for r in recs]
    assert "Month-to-month contract" in reasons
    assert "Short customer tenure" in reasons
    assert "No online security" in reasons
    assert "No technical support" in reasons
    assert "Electronic check" in reasons
    assert "High monthly charges" in reasons
    
    # All recommendations for HIGH risk must have URGENT urgency
    for r in recs:
        assert r.action_urgency == "URGENT"
        assert r.priority in {"High", "Medium", "Low"}
        assert r.customer_id == "HIGH-001"
        assert r.churn_probability == 0.88


def test_recommendations_with_shap_contributions():
    """Verify supporting SHAP contributions are attached when shap_row is supplied."""
    customer_data = {
        "Contract": "Month-to-month",
        "tenure": 5,
        "OnlineSecurity": "No",
        "TechSupport": "No",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 95.0
    }
    
    # Mock a SHAP series with positive contributions
    shap_row = pd.Series({
        "cat__Contract_Month-to-month": 0.4521,
        "num__tenure": 0.3120,
        "cat__OnlineSecurity_No": 0.1250,
        "cat__TechSupport_No": 0.1100,
        "cat__PaymentMethod_Electronic check": 0.0820,
        "num__MonthlyCharges": 0.2315
    })
    
    recs = RecommendationService.generate_customer_recommendations(
        customer_id="SHAP-CUST-1",
        customer_data=customer_data,
        churn_probability=0.79,
        risk_category="HIGH",
        shap_row=shap_row
    )
    
    assert len(recs) == 6
    for r in recs:
        assert r.supporting_shap_contribution is not None
        assert r.supporting_shap_contribution > 0
        assert r.shap_feature is not None


def test_recommendations_for_low_risk_loyal_customer():
    """Verify loyal low-risk customer with 2-year contract generates no unnecessary churn recommendations."""
    loyal_customer = {
        "Contract": "Two year",
        "tenure": 60,
        "OnlineSecurity": "Yes",
        "TechSupport": "Yes",
        "PaymentMethod": "Credit card (automatic)",
        "MonthlyCharges": 25.0
    }
    
    recs = RecommendationService.generate_customer_recommendations(
        customer_id="LOYAL-001",
        customer_data=loyal_customer,
        churn_probability=0.04,
        risk_category="LOW"
    )
    
    assert len(recs) == 0
