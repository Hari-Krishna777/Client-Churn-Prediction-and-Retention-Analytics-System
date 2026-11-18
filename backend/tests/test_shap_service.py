import pytest
import pandas as pd
from pathlib import Path

from app.services.feature_engineering import engineer_features
from app.services.shap_service import ShapService
from app.services.explanation_service import ExplanationService


@pytest.fixture
def sample_customers():
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    return engineer_features(df)


def test_shap_service_initialization_and_matrix(sample_customers):
    """Verify SHAP TreeExplainer calculates SHAP matrix correctly."""
    shap_df = ShapService.calculate_shap_matrix(sample_customers)
    
    # Check shape: 6 customers by 60 transformed features
    assert shap_df.shape[0] == len(sample_customers)
    assert shap_df.shape[1] == 60
    assert not shap_df.isnull().values.any()


def test_explanation_service_identifies_drivers_and_protective(sample_customers):
    """Verify ExplanationService extracts positive churn drivers and negative protective factors."""
    shap_df = ShapService.calculate_shap_matrix(sample_customers)
    
    # Customer 2280 is high churn risk (2754-SDJRD)
    cust_idx = 1
    shap_row = shap_df.iloc[cust_idx]
    
    drivers = ExplanationService.get_top_churn_drivers(shap_row, top_n=3)
    protective = ExplanationService.get_top_protective_factors(shap_row, top_n=3)
    
    assert len(drivers) == 3
    assert len(protective) == 3
    
    # Drivers must have positive contributions
    for d in drivers:
        assert d["contribution"] > 0
        assert d["direction"] == "increases_churn"
        assert isinstance(d["label"], str)
        assert len(d["label"]) > 0
        
    # Protective must have negative contributions
    for p in protective:
        assert p["contribution"] < 0
        assert p["direction"] == "decreases_churn"
        assert isinstance(p["label"], str)


def test_customer_explanation_json_format(sample_customers):
    """Verify customer explanation schema matches the required JSON structure."""
    shap_df = ShapService.calculate_shap_matrix(sample_customers)
    shap_row = shap_df.iloc[0]
    
    explanation = ExplanationService.explain_customer(
        customer_id="CUST001",
        churn_probability=0.72,
        shap_row=shap_row,
        top_n=3
    )
    
    dumped = explanation.model_dump()
    assert dumped["customer_id"] == "CUST001"
    assert dumped["churn_probability"] == 0.72
    assert "top_churn_factors" in dumped
    assert isinstance(dumped["top_churn_factors"], list)
    assert len(dumped["top_churn_factors"]) > 0
    # Factors should be human-readable
    assert not any("cat__" in factor for factor in dumped["top_churn_factors"])
    assert not any("num__" in factor for factor in dumped["top_churn_factors"])
