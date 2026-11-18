import io
import time
from pathlib import Path

import pandas as pd
import pytest

from tests.helpers import authenticated_client


@pytest.mark.performance
def test_large_csv_upload_completes_within_response_budget():
    """A 500-record upload is a practical regression guard for API throughput."""
    source = Path(__file__).parent / "data" / "sample_50_telco.csv"
    frame = pd.read_csv(source)
    large = pd.concat([frame] * 10, ignore_index=True)
    large["customerID"] = [f"PERF-{index:05d}" for index in range(len(large))]

    client = authenticated_client()
    started = time.monotonic()
    response = client.post(
        "/batch/predict",
        files={"file": ("large_telco.csv", io.BytesIO(large.to_csv(index=False).encode("utf-8")), "text/csv")},
    )
    elapsed = time.monotonic() - started

    assert response.status_code == 201, response.text
    assert response.json()["total_predictions"] == 500
    assert elapsed < 30, f"500-record upload took {elapsed:.2f}s"
