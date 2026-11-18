import logging
import joblib
import numpy as np
import pandas as pd
from app.config import (
    MODEL_PATH,
    DEFAULT_CLASSIFICATION_THRESHOLD,
    LOW_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    ALL_MODEL_FEATURES
)

logger = logging.getLogger(__name__)

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model bundle not found at {MODEL_PATH}")

model_bundle = joblib.load(MODEL_PATH)

model = model_bundle.get("model")
threshold = float(model_bundle.get("threshold", DEFAULT_CLASSIFICATION_THRESHOLD))


def get_risk_category(probability: float) -> str:
    """
    Classify churn risk category based on predicted probability.
    - LOW: < 0.30
    - MEDIUM: 0.30 to < 0.70
    - HIGH: >= 0.70
    """
    if probability < LOW_RISK_THRESHOLD:
        return "LOW"
    elif probability < HIGH_RISK_THRESHOLD:
        return "MEDIUM"
    else:
        return "HIGH"


def predict_churn(data: pd.DataFrame):
    """
    Generate churn probabilities and binary predictions using the loaded model.
    Accepts a DataFrame containing model features (original + engineered).
    Ensures feature columns match the order expected by the model.
    """
    # Align columns to the expected model feature names
    expected_features = getattr(model, "feature_names_in_", ALL_MODEL_FEATURES)
    aligned_data = data[expected_features]

    probabilities = model.predict_proba(aligned_data)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    return probabilities, predictions
