import io
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.connection import init_db
from app.main import app


def _new_user_client() -> TestClient:
    init_db()
    client = TestClient(app)
    suffix = uuid4().hex
    response = client.post(
        "/auth/register",
        json={
            "username": f"security_{suffix}",
            "email": f"security_{suffix}@example.test",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def _customer_payload(customer_id: str) -> dict:
    return {
        "customer_id": customer_id, "gender": "Female", "SeniorCitizen": 0,
        "Partner": "No", "Dependents": "No", "tenure": 5,
        "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "DSL",
        "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No",
        "TechSupport": "No", "StreamingTV": "No", "StreamingMovies": "No",
        "Contract": "Month-to-month", "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check", "MonthlyCharges": 65.0, "TotalCharges": 325.0,
    }


def test_customer_endpoints_require_a_bearer_token():
    client = TestClient(app)
    assert client.get("/customers").status_code == 401
    assert client.post("/predict", json=_customer_payload("unauthenticated")).status_code == 401


def test_users_cannot_read_another_users_customer_record():
    owner = _new_user_client()
    other = _new_user_client()
    customer_id = f"private-{uuid4().hex}"

    assert owner.post("/predict", json=_customer_payload(customer_id)).status_code == 200
    assert owner.get(f"/customers/{customer_id}").status_code == 200
    # Return 404 rather than confirming that another tenant owns the identifier.
    assert other.get(f"/customers/{customer_id}").status_code == 404
    assert all(item["customer_id"] != customer_id for item in other.get("/customers").json()["customers"])


def test_login_does_not_provision_unknown_users_and_bad_password_is_rejected():
    client = TestClient(app)
    unknown = client.post("/auth/login", json={"username": "does-not-exist", "password": "SecurePassword123!"})
    assert unknown.status_code == 401

    registered = _new_user_client()
    username = registered.get("/auth/me").json()["username"]
    bad_password = registered.post("/auth/login", json={"username": username, "password": "wrong-password"})
    assert bad_password.status_code == 401


def test_binary_and_non_utf8_uploads_are_rejected_after_authentication():
    client = _new_user_client()
    executable = client.post("/batch/predict", files={"file": ("payload.csv", io.BytesIO(b"MZ\x00bad"), "text/csv")})
    assert executable.status_code == 400

    non_utf8 = client.post("/batch/predict", files={"file": ("payload.csv", io.BytesIO(b"\xff\xfe\x00"), "text/csv")})
    assert non_utf8.status_code == 400
