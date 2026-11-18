import pytest
from tests.helpers import authenticated_client

client = authenticated_client()


def test_analytics_overview_endpoint():
    """Verify GET /analytics/overview returns valid metrics and risk distribution."""
    response = client.get("/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_customers" in data
    assert data["total_customers"] > 0
    assert "predicted_churners" in data
    assert "churn_rate_percentage" in data
    assert "average_churn_probability" in data
    assert "risk_distribution" in data
    assert "LOW" in data["risk_distribution"]
    assert "MEDIUM" in data["risk_distribution"]
    assert "HIGH" in data["risk_distribution"]
    assert data["classification_threshold"] == 0.40


def test_analytics_risk_distribution_endpoint():
    """Verify GET /analytics/risk-distribution returns counts, percentages, and definitions."""
    response = client.get("/analytics/risk-distribution")
    assert response.status_code == 200
    data = response.json()
    
    assert "counts" in data
    assert "percentages" in data
    assert "thresholds" in data
    assert "descriptions" in data
    
    assert data["thresholds"]["low_risk_max"] == 0.30
    assert data["thresholds"]["high_risk_min"] == 0.70
    assert data["thresholds"]["binary_classification_threshold"] == 0.40
    
    # Percentages should sum approximately to 100
    total_pct = sum(data["percentages"].values())
    assert 99.0 <= total_pct <= 101.0


def test_analytics_churn_factors_endpoint():
    """Verify GET /analytics/churn-factors returns SHAP-derived churn drivers and protective factors."""
    response = client.get("/analytics/churn-factors?top_n=5")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_analyzed"] > 0
    assert "top_churn_drivers" in data
    assert len(data["top_churn_drivers"]) <= 5
    assert "top_protective_factors" in data
    assert len(data["top_protective_factors"]) <= 5
    
    # Check driver structure
    driver = data["top_churn_drivers"][0]
    assert "factor" in driver
    assert "feature_name" in driver
    assert "impact_score" in driver
    assert "affected_customers_count" in driver
    assert driver["direction"] == "increases_churn"


def test_analytics_recommendations_summary_endpoint():
    """Verify GET /analytics/recommendations returns aggregated retention insights."""
    response = client.get("/analytics/recommendations")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_recommendations"] > 0
    assert data["unique_customers_receiving_recommendations"] > 0
    assert "by_reason" in data
    assert "by_priority" in data
    assert "by_urgency" in data
    assert "top_suggested_actions" in data
    assert len(data["top_suggested_actions"]) > 0


def test_analytics_segments_endpoint():
    """Verify GET /analytics/segments returns breakdown across dimensions."""
    response = client.get("/analytics/segments")
    assert response.status_code == 200
    data = response.json()
    
    assert "by_contract" in data
    assert len(data["by_contract"]) > 0
    assert "by_tenure_group" in data
    assert len(data["by_tenure_group"]) > 0
    assert "by_internet_service" in data
    assert "by_payment_method" in data
    assert "highest_risk_segments" in data
    
    first_contract = data["by_contract"][0]
    assert "segment_name" in first_contract
    assert "customer_count" in first_contract
    assert "churn_rate_percentage" in first_contract


def test_predict_with_explain_flag():
    """Verify POST /predict?explain=true returns SHAP factors and recommendations."""
    payload = {
        "customer_id": "EXPLAIN-001",
        "gender": "Male",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 2,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 89.0,
        "TotalCharges": 178.0
    }
    
    response = client.post("/predict?explain=true", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["customer_id"] == "EXPLAIN-001"
    assert "top_churn_factors" in data
    assert isinstance(data["top_churn_factors"], list)
    assert len(data["top_churn_factors"]) > 0
    assert "action_urgency" in data
    assert data["action_urgency"] in {"URGENT", "PLANNED", "MONITOR"}
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0


def test_dedicated_recommendations_endpoint():
    """Verify POST /predict/recommendations returns dedicated prioritized strategy."""
    payload = {
        "customer_id": "REC-001",
        "gender": "Female",
        "SeniorCitizen": 1,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 4,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 75.0,
        "TotalCharges": 300.0
    }
    
    response = client.post("/predict/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["customer_id"] == "REC-001"
    assert data["total_recommendations"] > 0
    assert data["action_urgency"] in {"URGENT", "PLANNED", "MONITOR"}
    assert len(data["recommendations"]) > 0
    first_rec = data["recommendations"][0]
    assert "recommendation_reason" in first_rec
    assert "suggested_action" in first_rec
    assert "priority" in first_rec
    assert "action_urgency" in first_rec
