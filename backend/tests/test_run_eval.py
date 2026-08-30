"""
Tests for the benchmark evaluation harness.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.tests.benchmark.run_eval import evaluate_record, run_benchmark


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
        {
            "query": "q1",
            "stratum": "in-coverage",
            "expected_state": "ANSWERED",
            "expected_standard": "IS 1234",
            "expected_mandatory": True,
            "min_authoritative_evidence": 1,
            "benchmark_version": "v1.0",
        },
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


@patch("backend.tests.benchmark.run_eval.httpx.AsyncClient")
def test_run_benchmark_stratum_separation(mock_async_client_class: MagicMock, dummy_benchmark_data: Path, tmp_path: Path) -> None:
    """Verify that run_benchmark groups metrics by stratum and doesn't blend them."""
    mock_client = MagicMock()
    mock_async_client_class.return_value.__aenter__.return_value = mock_client
    
    async def fake_post(url: str, json: dict[str, str]) -> MagicMock:
        q = json.get("query")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        
        # q1: Pass
        if q == "q1":
            mock_resp.json.return_value = {
                "state": "ANSWERED",
                "explanation": "Success",
                "decision": {
                    "standard": "IS 1234",
                    "mandatory": True,
                    "basis": None,
                    "effective_from": None,
                    "pathway": None,
                    "confidence": "HIGH",
                },
                "evidence": [
                    {
                        "source_id": "ev1",
                        "source_type": "qco_gazette",
                        "content": "Official evidence",
                        "authoritative": True,
                    }
                ],
            }
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
    assert "metrics_by_task" in report
    assert "failure_decomposition" in report
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
    assert report["failures"][0]["failure_type"] == "retrieval_or_routing_failure"


def test_evaluate_record_uses_structured_decision_not_explanation() -> None:
    """Expected standards are checked against the API decision object."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "state": "ANSWERED",
        "explanation": "The generated response omitted the standard identifier.",
        "decision": {
            "standard": "IS-1234",
            "mandatory": True,
            "basis": "QCO-TOYS",
            "confidence": "HIGH",
        },
        "evidence": [{"authoritative": True}],
    }

    result = evaluate_record(
        {
            "expected_state": "ANSWERED",
            "expected_standard": "IS 1234",
            "expected_mandatory": True,
            "expected_basis": "QCO TOYS",
            "expected_confidence": "HIGH",
            "min_authoritative_evidence": 1,
        },
        resp,
    )

    assert result["passed"] is True
    assert result["checks"]["decision"] is True
    assert result["checks"]["citation"] is True


def test_evaluate_record_flags_forbidden_identifier() -> None:
    """Adversarial records can guard against fabricated identifiers."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "state": "NOT_FOUND",
        "explanation": "No match found for IS 99999:2026.",
        "decision": None,
        "evidence": [],
    }

    result = evaluate_record(
        {
            "expected_state": "NOT_FOUND",
            "forbidden_identifiers": ["IS 99999:2026"],
        },
        resp,
    )

    assert result["passed"] is False
    assert result["checks"]["hallucination"] is False
    assert result["failure_type"] == "generation_failure"
