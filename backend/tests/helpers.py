"""Shared authenticated API client for endpoint tests."""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.connection import init_db
from app.main import app


def authenticated_client() -> TestClient:
    init_db()
    client = TestClient(app)
    suffix = uuid4().hex
    response = client.post(
        "/auth/register",
        json={
            "username": f"test_{suffix}",
            "email": f"test_{suffix}@example.test",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
