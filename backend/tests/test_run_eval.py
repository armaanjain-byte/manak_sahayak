"""
Tests for the benchmark evaluation harness.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.tests.benchmark.run_eval import run_benchmark


@pytest.fixture
def dummy_benchmark_data(tmp_path: Path) -> Path:
    """Creates a temporary benchmark data directory with dummy queries."""
    data_dir = tmp_path / "benchmark"
    data_dir.mkdir()
    
    meta = {
        "benchmark_version": "v1.0",
        "taxonomy_version": "v1.0",
    }
    with (data_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f)
        
    queries = [
        # Pass (in-coverage)
        {"query": "q1", "stratum": "in-coverage", "expected_state": "ANSWERED", "benchmark_version": "v1.0"},
        # Fail (in-coverage)
        {"query": "q2", "stratum": "in-coverage", "expected_state": "ANSWERED", "benchmark_version": "v1.0"},
        # Pass (out-of-coverage)
        {"query": "q3", "stratum": "out-of-coverage", "expected_state": "NOT_FOUND", "benchmark_version": "v1.0"},
        # Version mismatch warning, but still executed and passed
        {"query": "q4", "stratum": "out-of-coverage", "expected_state": "NOT_FOUND", "benchmark_version": "v9.9"},
    ]
    
    with (data_dir / "eval_queries.jsonl").open("w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")
            
    return data_dir


@patch("backend.tests.benchmark.run_eval.TestClient")
def test_run_benchmark_stratum_separation(mock_test_client_class: MagicMock, dummy_benchmark_data: Path, tmp_path: Path) -> None:
    """Verify that run_benchmark groups metrics by stratum and doesn't blend them."""
    mock_client = MagicMock()
    mock_test_client_class.return_value = mock_client
    
    def fake_post(url: str, json: dict[str, str]) -> MagicMock:
        q = json.get("query")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        # q1: Pass
        if q == "q1":
            mock_resp.json.return_value = {"state": "ANSWERED", "explanation": "Success"}
        # q2: Fail
        elif q == "q2":
            mock_resp.json.return_value = {"state": "NOT_FOUND", "explanation": "Fail"}
        # q3, q4: Pass
        else:
            mock_resp.json.return_value = {"state": "NOT_FOUND", "explanation": "Pass"}
            
        return mock_resp

    mock_client.post.side_effect = fake_post
    
    report_file = tmp_path / "report.json"
    run_benchmark(dummy_benchmark_data, report_file)
    
    assert report_file.exists()
    
    with report_file.open(encoding="utf-8") as f:
        report = json.load(f)
        
    assert "metrics_by_stratum" in report
    metrics = report["metrics_by_stratum"]
    
    # In-coverage: 1 pass, 1 fail
    assert metrics["in-coverage"]["total"] == 2
    assert metrics["in-coverage"]["pass"] == 1
    assert metrics["in-coverage"]["fail"] == 1
    
    # Out-of-coverage: 2 pass, 0 fail
    assert metrics["out-of-coverage"]["total"] == 2
    assert metrics["out-of-coverage"]["pass"] == 2
    assert metrics["out-of-coverage"]["fail"] == 0
    
    # Failures list should contain q2
    assert len(report["failures"]) == 1
    assert report["failures"][0]["query"] == "q2"
