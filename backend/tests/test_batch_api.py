import io
import pytest
import pandas as pd
from pathlib import Path
from tests.helpers import authenticated_client

client = authenticated_client()


@pytest.fixture
def sample_csv_bytes():
    sample_path = Path(__file__).resolve().parent / "data" / "sample_50_telco.csv"
    with open(sample_path, "rb") as f:
        return f.read()


def test_batch_predict_valid_csv(sample_csv_bytes):
    """Test full workflow of uploading a valid 50-row CSV file."""
    files = {
        "file": ("telco_batch.csv", io.BytesIO(sample_csv_bytes), "text/csv")
    }
    response = client.post("/batch/predict", files=files)
    assert response.status_code == 201
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "COMPLETED"
    assert data["filename"] == "telco_batch.csv"
    assert data["total_predictions"] == 50
    
    summary = data["validation_summary"]
    assert summary["total_records"] == 50
    assert summary["valid_records"] == 50
    assert summary["invalid_records"] == 0
    assert summary["duplicate_records"] == 0
    assert summary["successfully_processed"] == 50
    
    risk_dist = data["risk_distribution"]
    assert "LOW" in risk_dist
    assert "MEDIUM" in risk_dist
    assert "HIGH" in risk_dist
    assert sum(risk_dist.values()) == 50


def test_get_batch_status_and_results(sample_csv_bytes):
    """Test retrieving status, paginated results, and verifying response format."""
    files = {
        "file": ("telco_batch_2.csv", io.BytesIO(sample_csv_bytes), "text/csv")
    }
    create_res = client.post("/batch/predict", files=files)
    assert create_res.status_code == 201
    job_id = create_res.json()["job_id"]
    
    # 1. Check status endpoint
    status_res = client.get(f"/batch/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert status_data["total_records"] == 50
    assert status_data["successfully_processed"] == 50
    
    # 2. Check results endpoint (pagination: limit 10, offset 0)
    res_page_1 = client.get(f"/batch/{job_id}/results?limit=10&offset=0")
    assert res_page_1.status_code == 200
    page_1_data = res_page_1.json()
    assert page_1_data["total_predictions"] == 50
    assert len(page_1_data["predictions"]) == 10
    
    first_item = page_1_data["predictions"][0]
    assert "customer_id" in first_item
    assert "churn_probability" in first_item
    assert "churn_prediction" in first_item
    assert "risk_category" in first_item
    assert "TenureGroup" in first_item
    assert "AvgMonthlySpend" in first_item
    assert "ServiceCount" in first_item
    
    # 3. Check page 2
    res_page_2 = client.get(f"/batch/{job_id}/results?limit=15&offset=10")
    assert res_page_2.status_code == 200
    page_2_data = res_page_2.json()
    assert len(page_2_data["predictions"]) == 15


def test_download_batch_csv(sample_csv_bytes):
    """Test downloading prediction results as CSV."""
    files = {
        "file": ("telco_for_download.csv", io.BytesIO(sample_csv_bytes), "text/csv")
    }
    create_res = client.post("/batch/predict", files=files)
    job_id = create_res.json()["job_id"]
    
    download_res = client.get(f"/batch/{job_id}/download")
    assert download_res.status_code == 200
    assert "text/csv" in download_res.headers["content-type"]
    assert f"churn_predictions_{job_id}.csv" in download_res.headers.get("content-disposition", "")
    
    # Parse downloaded CSV content
    downloaded_df = pd.read_csv(io.StringIO(download_res.text))
    assert len(downloaded_df) == 50
    assert "customer_id" in downloaded_df.columns
    assert "churn_probability" in downloaded_df.columns
    assert "churn_prediction" in downloaded_df.columns
    assert "risk_category" in downloaded_df.columns
    assert "TenureGroup" in downloaded_df.columns
    assert "AvgMonthlySpend" in downloaded_df.columns
    assert "ServiceCount" in downloaded_df.columns


def test_reject_non_csv_extension():
    """Verify non-csv uploads are rejected with 400 Bad Request."""
    files = {
        "file": ("data.json", io.BytesIO(b'{"test": 123}'), "application/json")
    }
    response = client.post("/batch/predict", files=files)
    assert response.status_code == 400
    assert "must have a .csv extension" in response.json()["detail"]


def test_reject_empty_csv():
    """Verify 0-byte CSV uploads are rejected."""
    files = {
        "file": ("empty.csv", io.BytesIO(b""), "text/csv")
    }
    response = client.post("/batch/predict", files=files)
    assert response.status_code == 400
    assert "Empty CSV file" in response.json()["detail"]


def test_batch_predict_with_invalid_and_duplicate_rows():
    """Verify reporting when some rows fail validation or are duplicates."""
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path, dtype=object).head(2).copy()
    
    # Row 1: valid
    # Row 2: invalid gender
    df.loc[1, "gender"] = "InvalidGender"
    
    # Row 3: duplicate of Row 1
    dup_row = df.iloc[[0]].copy()
    combined_df = pd.concat([df, dup_row], ignore_index=True)
    
    csv_bytes = combined_df.to_csv(index=False).encode("utf-8")
    files = {
        "file": ("mixed_test.csv", io.BytesIO(csv_bytes), "text/csv")
    }
    
    response = client.post("/batch/predict", files=files)
    assert response.status_code == 201
    
    data = response.json()
    summary = data["validation_summary"]
    assert summary["total_records"] == 3
    assert summary["valid_records"] == 1
    assert summary["invalid_records"] == 1
    assert summary["duplicate_records"] == 1
    assert summary["successfully_processed"] == 1
    
    assert len(data["invalid_records"]) == 2
    # Check explanations exist
    all_reasons = [r for err in data["invalid_records"] for r in err["reasons"]]
    assert any("InvalidGender" in r for r in all_reasons)
    assert any("Duplicate customer record" in r for r in all_reasons)


def test_job_not_found_returns_404():
    """Verify 404 for unknown job ID."""
    res_status = client.get("/batch/non-existent-id")
    assert res_status.status_code == 404
    
    res_results = client.get("/batch/non-existent-id/results")
    assert res_results.status_code == 404
    
    res_download = client.get("/batch/non-existent-id/download")
    assert res_download.status_code == 404
