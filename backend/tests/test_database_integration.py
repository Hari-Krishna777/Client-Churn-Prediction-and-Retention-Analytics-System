import io
import pytest
from sqlalchemy import inspect
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal, engine, init_db
from app.database.models import User, Dataset, Customer, Prediction, Recommendation, BatchJobModel
from app.repositories.user_repository import UserRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.batch_repository import BatchRepository
from tests.helpers import authenticated_client

client = authenticated_client()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


def test_database_tables_exist():
    """Verify all 7 database tables are created and recognized by SQLAlchemy."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    expected_tables = [
        "users",
        "datasets",
        "customers",
        "predictions",
        "recommendations",
        "prediction_explanations",
        "batch_jobs"
    ]
    for tbl in expected_tables:
        assert tbl in tables, f"Expected table '{tbl}' not found in database"


def test_user_repository_crud():
    """Verify user creation, retrieval, and default user provisioning."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        # 1. Default analyst user
        default_user = UserRepository.get_or_create_default_user(db)
        assert default_user is not None
        assert default_user.username == "default_analyst"

        # 2. Custom user creation
        custom_user = UserRepository.create(
            db=db,
            username=f"analyst_{suffix}",
            email=f"analyst_{suffix}@churniq.io",
            role="analyst"
        )
        assert custom_user.id is not None
        
        # 3. Lookup
        found = UserRepository.get_by_username(db, f"analyst_{suffix}")
        assert found is not None
        assert found.email == f"analyst_{suffix}@churniq.io"


def test_dataset_repository_crud_and_retention_policy():
    """Verify dataset CRUD, soft deletion policy, and hard deletion cascade."""
    with SessionLocal() as db:
        # Create dataset
        ds = DatasetRepository.create(
            db=db,
            name="Q3_Customers_2026",
            filename="q3_customers.csv",
            total_records=100,
            valid_records=95,
            invalid_records=5
        )
        assert ds.id is not None
        assert ds.is_deleted is False

        # Soft delete (retention policy)
        soft_ok = DatasetRepository.soft_delete(db, ds.id)
        assert soft_ok is True
        
        # Listing without deleted
        active_list, _ = DatasetRepository.list_datasets(db, include_deleted=False)
        assert not any(d.id == ds.id for d in active_list)
        
        # Listing with deleted
        full_list, _ = DatasetRepository.list_datasets(db, include_deleted=True)
        assert any(d.id == ds.id for d in full_list)

        # Hard delete
        hard_ok = DatasetRepository.hard_delete(db, ds.id)
        assert hard_ok is True
        assert DatasetRepository.get_by_id(db, ds.id) is None


def test_customer_prediction_and_recommendation_relationships():
    """Verify foreign key relations: Customer -> Prediction -> Recommendations & Explanations."""
    with SessionLocal() as db:
        # Create dataset
        ds = DatasetRepository.create(db, name="Rel_Test", filename="rel_test.csv")
        
        # Create customer
        cust = CustomerRepository.create(
            db=db,
            customer_id="REL-CUST-001",
            customer_dict={
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 6,
                "Contract": "Month-to-month",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 75.0,
                "TotalCharges": 450.0
            },
            dataset_id=ds.id
        )
        assert cust.id is not None

        # Create prediction with explanations
        explanations = [
            {"feature_name": "cat__Contract_Month-to-month", "feature_label": "Month-to-month contract", "contribution": 0.35, "direction": "increases_churn"},
            {"feature_name": "num__tenure", "feature_label": "Short customer tenure", "contribution": 0.22, "direction": "increases_churn"}
        ]
        pred = PredictionRepository.create(
            db=db,
            customer_id=cust.id,
            dataset_id=ds.id,
            churn_probability=0.78,
            churn_prediction="Yes",
            risk_category="HIGH",
            action_urgency="URGENT",
            tenure_group="0-6 months",
            avg_monthly_spend=75.0,
            service_count=2,
            explanations=explanations
        )
        assert pred.id is not None
        assert len(pred.explanations) == 2

        # Create recommendation
        rec = RecommendationRepository.create(
            db=db,
            prediction_id=pred.id,
            customer_id=cust.id,
            recommendation_reason="Month-to-month contract",
            suggested_action="Offer a longer-term contract",
            priority="High",
            action_urgency="URGENT",
            supporting_shap_contribution=0.35,
            shap_feature="cat__Contract_Month-to-month"
        )
        assert rec.id is not None
        assert rec.prediction.id == pred.id
        assert rec.customer.id == cust.id


def test_prediction_history_tracking():
    """Verify tracking multiple prediction snapshots over time for a customer."""
    with SessionLocal() as db:
        cust = CustomerRepository.create(
            db=db,
            customer_id="HIST-CUST-999",
            customer_dict={"tenure": 10, "MonthlyCharges": 60.0, "TotalCharges": 600.0}
        )
        
        # Prediction snapshot 1 (Month 10)
        p1 = PredictionRepository.create(
            db=db,
            customer_id=cust.id,
            churn_probability=0.85,
            churn_prediction="Yes",
            risk_category="HIGH",
            action_urgency="URGENT"
        )
        
        # Prediction snapshot 2 (Month 12, customer took retention offer)
        p2 = PredictionRepository.create(
            db=db,
            customer_id=cust.id,
            churn_probability=0.25,
            churn_prediction="No",
            risk_category="LOW",
            action_urgency="MONITOR"
        )
        
        history = PredictionRepository.get_customer_prediction_history(db, cust.id)
        assert len(history) >= 2
        # First in list should be latest
        assert history[0].id == p2.id
        assert history[0].churn_probability == 0.25
        assert history[1].id == p1.id
        assert history[1].churn_probability == 0.85


def test_datasets_and_customers_api_endpoints():
    """Verify HTTP endpoints for dataset listing, customer search, and prediction history."""
    # 1. List datasets
    res_ds = client.get("/datasets")
    assert res_ds.status_code == 200
    assert "datasets" in res_ds.json()

    # 2. List customers
    res_cust = client.get("/customers?limit=10")
    assert res_cust.status_code == 200
    assert "customers" in res_cust.json()

    # 3. Predict customer and check history endpoint
    payload = {
        "customer_id": "API-HIST-CUST-1",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 5,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 65.0,
        "TotalCharges": 325.0
    }
    pred_res = client.post("/predict?explain=true", json=payload)
    assert pred_res.status_code == 200

    # Retrieve history
    hist_res = client.get("/predict/history/API-HIST-CUST-1")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["customer_id"] == "API-HIST-CUST-1"
    assert hist_data["total_historical_predictions"] >= 1
