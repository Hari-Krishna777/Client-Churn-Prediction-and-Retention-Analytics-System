import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Base directories
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")
MODELS_DIR = PROJECT_DIR / "models"
STORAGE_DIR = BACKEND_DIR / "storage" / "batch_jobs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Model configuration
DEFAULT_MODEL_PATH = MODELS_DIR / "churn_model_bundle.joblib"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))

# Risk and prediction thresholds
LOW_RISK_THRESHOLD = float(os.getenv("LOW_RISK_THRESHOLD", "0.30"))
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "0.70"))
DEFAULT_CLASSIFICATION_THRESHOLD = 0.40

# Security and privacy configuration.  A real secret is mandatory in production;
# the short-lived development key deliberately cannot be shared between runs.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
_configured_jwt_secret = os.getenv("JWT_SECRET_KEY")
if ENVIRONMENT == "production" and not _configured_jwt_secret:
    raise RuntimeError("JWT_SECRET_KEY must be configured when ENVIRONMENT=production.")
JWT_SECRET_KEY = _configured_jwt_secret or secrets.token_urlsafe(48)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))  # 50 MB
DATASET_RETENTION_DAYS = int(os.getenv("DATASET_RETENTION_DAYS", "30"))
ENABLE_SECURITY_HEADERS = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() in {"1", "true", "yes"}
HTTPS_ENFORCE = os.getenv("HTTPS_ENFORCE", "true" if ENVIRONMENT == "production" else "false").lower() in {"1", "true", "yes"}
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host.strip()]

# The 19 original input features
INPUT_NUMERIC_FEATURES = [
    "SeniorCitizen",
    "tenure",
    "MonthlyCharges",
    "TotalCharges"
]

INPUT_CATEGORICAL_FEATURES = [
    "gender",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod"
]

ALL_INPUT_FEATURES = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges"
]

# Engineered features
ENGINEERED_FEATURES = [
    "TenureGroup",
    "AvgMonthlySpend",
    "ServiceCount"
]

# Full 22 features expected by the trained pipeline
ALL_MODEL_FEATURES = ALL_INPUT_FEATURES + ENGINEERED_FEATURES

# The 8 service columns used to compute ServiceCount
SERVICE_COLUMNS = [
    "PhoneService",
    "MultipleLines",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies"
]

# TenureGroup bins and labels
TENURE_BINS = [-1, 6, 12, 24, 48, 72]
TENURE_LABELS = [
    "0-6 months",
    "7-12 months",
    "13-24 months",
    "25-48 months",
    "49-72 months"
]

# Valid categorical domain values
VALID_CATEGORICAL_VALUES = {
    "gender": {"Male", "Female"},
    "SeniorCitizen": {0, 1},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "PhoneService": {"Yes", "No"},
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "OnlineSecurity": {"Yes", "No", "No internet service"},
    "OnlineBackup": {"Yes", "No", "No internet service"},
    "DeviceProtection": {"Yes", "No", "No internet service"},
    "TechSupport": {"Yes", "No", "No internet service"},
    "StreamingTV": {"Yes", "No", "No internet service"},
    "StreamingMovies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": {"Yes", "No"},
    "PaymentMethod": {
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)"
    }
}

# Supported customer identifier column aliases
CUSTOMER_ID_COLUMNS = ["customerID", "customer_id", "CustomerID", "id", "ID"]
