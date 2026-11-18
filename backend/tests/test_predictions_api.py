import pytest
from tests.helpers import authenticated_client

client = authenticated_client()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["app"] == "ChurnIQ API"


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["threshold"] == 0.4


def test_single_customer_predict_endpoint():
    customer_payload = {
        "customer_id": "TEST-CUST-001",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 12,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 70.35,
        "TotalCharges": 845.5
    }
    
    response = client.post("/predict", json=customer_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "TEST-CUST-001"
    assert "churn_probability" in data
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["churn_prediction"] in {"Yes", "No"}
    assert data["risk_category"] in {"LOW", "MEDIUM", "HIGH"}
    assert data["threshold"] == 0.4


def test_single_customer_predict_validation_error():
    """Verify pydantic validation rejects invalid payloads."""
    invalid_payload = {
        "gender": "Female",
        "tenure": -5  # Invalid negative tenure
    }
    response = client.post("/predict", json=invalid_payload)
    assert response.status_code == 422
