import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from xgboost import XGBClassifier

from app.config import (
    MODEL_PATH,
    ALL_INPUT_FEATURES,
    ENGINEERED_FEATURES,
    ALL_MODEL_FEATURES,
    INPUT_NUMERIC_FEATURES,
    INPUT_CATEGORICAL_FEATURES,
    SERVICE_COLUMNS,
    TENURE_BINS,
    TENURE_LABELS,
    VALID_CATEGORICAL_VALUES,
    LOW_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD
)
from app.services.model_service import model, threshold, get_risk_category, predict_churn
from app.services.feature_engineering import engineer_features


def test_model_artifact_integrity():
    """Verify that the model file exists, is valid, and contains expected components."""
    assert MODEL_PATH.exists(), f"Model artifact missing at {MODEL_PATH}"
    assert isinstance(model, Pipeline), "Model is not an sklearn Pipeline"
    assert threshold == 0.4, f"Expected threshold 0.4, got {threshold}"
    
    # Verify pipeline steps
    step_names = [name for name, _ in model.steps]
    assert "preprocessor" in step_names, "Missing preprocessor in pipeline"
    assert "model" in step_names, "Missing model step in pipeline"
    
    preprocessor = model.named_steps["preprocessor"]
    assert isinstance(preprocessor, ColumnTransformer), "Preprocessor is not a ColumnTransformer"
    
    final_estimator = model.named_steps["model"]
    assert isinstance(final_estimator, XGBClassifier), "Final model is not an XGBClassifier"


def test_all_19_original_input_features():
    """Verify all 19 original Telco features are recognized and handled."""
    assert len(ALL_INPUT_FEATURES) == 19
    assert len(INPUT_NUMERIC_FEATURES) == 4
    assert len(INPUT_CATEGORICAL_FEATURES) == 15
    
    model_features = list(model.feature_names_in_)
    for feat in ALL_INPUT_FEATURES:
        assert feat in model_features, f"Input feature '{feat}' not in model feature list"


def test_the_three_engineered_features():
    """Verify the 3 engineered features exist in model expectations."""
    assert len(ENGINEERED_FEATURES) == 3
    assert set(ENGINEERED_FEATURES) == {"TenureGroup", "AvgMonthlySpend", "ServiceCount"}
    
    model_features = list(model.feature_names_in_)
    for feat in ENGINEERED_FEATURES:
        assert feat in model_features, f"Engineered feature '{feat}' not in model feature list"
    
    assert len(model_features) == 22, f"Expected exactly 22 model features, found {len(model_features)}"


def test_feature_ordering_matches_contract():
    """Verify feature ordering strictly matches model.feature_names_in_."""
    expected_order = [
        "gender", "SeniorCitizen", "Partner", "Dependents", "tenure", "PhoneService",
        "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
        "Contract", "PaperlessBilling", "PaymentMethod", "MonthlyCharges",
        "TotalCharges", "TenureGroup", "AvgMonthlySpend", "ServiceCount"
    ]
    assert list(model.feature_names_in_) == expected_order
    assert ALL_MODEL_FEATURES == expected_order


def test_tenure_group_boundaries():
    """Confirm exact TenureGroup boundaries: [-1, 6, 12, 24, 48, 72]."""
    test_tenures = [0, 6, 7, 12, 13, 24, 25, 48, 49, 72]
    expected_groups = [
        "0-6 months", "0-6 months",
        "7-12 months", "7-12 months",
        "13-24 months", "13-24 months",
        "25-48 months", "25-48 months",
        "49-72 months", "49-72 months"
    ]
    
    df = pd.DataFrame({
        "tenure": test_tenures,
        "TotalCharges": [100.0] * len(test_tenures),
        "MonthlyCharges": [50.0] * len(test_tenures),
        **{col: ["No"] * len(test_tenures) for col in SERVICE_COLUMNS}
    })
    
    eng = engineer_features(df)
    assert list(eng["TenureGroup"]) == expected_groups


def test_avg_monthly_spend_calculation():
    """Confirm AvgMonthlySpend calculation when tenure > 0 vs tenure == 0."""
    df = pd.DataFrame({
        "tenure": [0, 10, 24],
        "TotalCharges": [0.0, 500.0, 1200.0],
        "MonthlyCharges": [45.0, 60.0, 55.0],
        **{col: ["No"] * 3 for col in SERVICE_COLUMNS}
    })
    
    eng = engineer_features(df)
    # When tenure is 0: fallback to MonthlyCharges (45.0)
    assert eng.loc[0, "AvgMonthlySpend"] == 45.0
    # When tenure is 10: 500 / 10 = 50.0
    assert eng.loc[1, "AvgMonthlySpend"] == 50.0
    # When tenure is 24: 1200 / 24 = 50.0
    assert eng.loc[2, "AvgMonthlySpend"] == 50.0


def test_service_count_calculation():
    """Confirm ServiceCount counts 'Yes' accurately across the 8 service features."""
    df = pd.DataFrame({
        "tenure": [12, 12, 12],
        "TotalCharges": [600.0, 600.0, 600.0],
        "MonthlyCharges": [50.0, 50.0, 50.0],
        "PhoneService": ["Yes", "No", "Yes"],
        "MultipleLines": ["Yes", "No phone service", "No"],
        "OnlineSecurity": ["Yes", "No internet service", "Yes"],
        "OnlineBackup": ["Yes", "No", "No"],
        "DeviceProtection": ["Yes", "No internet service", "No"],
        "TechSupport": ["Yes", "No", "No"],
        "StreamingTV": ["Yes", "No internet service", "No"],
        "StreamingMovies": ["Yes", "No", "Yes"]
    })
    
    eng = engineer_features(df)
    # Row 0: all 8 "Yes" -> 8
    assert eng.loc[0, "ServiceCount"] == 8
    # Row 1: no "Yes" -> 0
    assert eng.loc[1, "ServiceCount"] == 0
    # Row 2: 3 "Yes" -> 3
    assert eng.loc[2, "ServiceCount"] == 3


def test_categorical_domain_values():
    """Verify categorical domains in ColumnTransformer OneHotEncoder match configuration."""
    preprocessor = model.named_steps["preprocessor"]
    ohe = preprocessor.named_transformers_["cat"].named_steps["encoder"]
    cat_columns = preprocessor.transformers[1][2]
    
    for col, categories in zip(cat_columns, ohe.categories_):
        cat_set = set(categories)
        if col in VALID_CATEGORICAL_VALUES:
            expected = VALID_CATEGORICAL_VALUES[col]
            assert expected.issubset(cat_set) or cat_set == expected, (
                f"Mismatch for column '{col}': expected {expected}, got {cat_set}"
            )


def test_deepnote_prediction_consistency():
    """Compare backend model predictions against original Deepnote notebook benchmark."""
    cases_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    assert cases_path.exists(), "deepnote_cases.csv not found"
    
    df = pd.read_csv(cases_path)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    
    eng = engineer_features(df)
    probs, preds = predict_churn(eng)
    
    # Deepnote benchmarks:
    # 4376-KFVRS -> Low risk (~0.012), Churn No
    # 2754-SDJRD -> High risk (~0.95), Churn Yes
    # 4686-UXDML -> High risk (~0.81), Churn Yes
    # 9385-NXKDA -> Low risk (~0.01), Churn No
    
    results = dict(zip(df["customerID"], probs))
    
    assert results["4376-KFVRS"] < LOW_RISK_THRESHOLD
    assert get_risk_category(results["4376-KFVRS"]) == "LOW"
    
    assert results["2754-SDJRD"] >= HIGH_RISK_THRESHOLD
    assert get_risk_category(results["2754-SDJRD"]) == "HIGH"
    
    assert results["4686-UXDML"] >= HIGH_RISK_THRESHOLD
    assert get_risk_category(results["4686-UXDML"]) == "HIGH"
    
    assert results["9385-NXKDA"] < LOW_RISK_THRESHOLD
    assert get_risk_category(results["9385-NXKDA"]) == "LOW"
