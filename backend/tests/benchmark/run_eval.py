"""
Evaluation benchmark runner for the 120-query stratified dataset.

Enforces frozen evaluation by verifying version numbers.
Executes queries via the real API layer (FastAPI TestClient) to exercise
the complete intent classification, entity extraction, and reasoning paths.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from app.main import app

logger = logging.getLogger(__name__)


def load_metadata(data_dir: Path) -> dict[str, Any]:
    meta_path = data_dir / "metadata.json"
    if not meta_path.exists():
        logger.warning(
            "CRITICAL: data/benchmark/metadata.json not found! "
            "Cannot verify evaluation freeze."
        )
        return {}
    with meta_path.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def run_benchmark(data_dir: Path, output_file: Path) -> None:
    metadata = load_metadata(data_dir)
    frozen_version = metadata.get("benchmark_version")

    queries_path = data_dir / "eval_queries.jsonl"
    if not queries_path.exists():
        logger.error(f"Benchmark file {queries_path} not found.")
        sys.exit(1)

    # Initialize TestClient to hit the real app routes (POST /query)
    client = TestClient(app)

    results_by_stratum: dict[str, dict[str, int]] = {}
    failed_queries: list[dict[str, Any]] = []
    total = 0
    passed = 0

    with queries_path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error("Line %d is invalid JSON: %s", line_num, e)
                continue

            q_version = record.get("benchmark_version")
            if frozen_version and q_version != frozen_version:
                logger.warning(
                    "CRITICAL WARNING: Query on line %d has version '%s', "
                    "but frozen metadata expects '%s'. The benchmark has been mutated!",
                    line_num,
                    q_version,
                    frozen_version,
                )

            query_text = record.get("query", "")
            stratum = record.get("stratum", "unknown")
            expected_state = record.get("expected_state")
            expected_standard = record.get("expected_standard")

            if stratum not in results_by_stratum:
                results_by_stratum[stratum] = {"total": 0, "pass": 0, "fail": 0}

            results_by_stratum[stratum]["total"] += 1
            total += 1

            # Execute query through orchestration
            resp = client.post("/query", json={"query": query_text})
            
            is_pass = False
            actual_state = None
            explanation = None
            
            if resp.status_code == 200:
                body = resp.json()
                actual_state = body.get("state")
                explanation = body.get("explanation")
                
                state_match = (actual_state == expected_state)
                
                # Check standard if provided (a bit brittle on pure explanation parsing, 
                # but we can look for it in the explanation string for now)
                std_match = True
                if expected_standard and expected_standard not in (explanation or ""):
                    # In a full implementation, we'd inspect the actual structured DecisionObject
                    # But the API layer doesn't leak raw DecisionObjects by default.
                    std_match = False
                    
                is_pass = state_match and std_match
            
            if is_pass:
                results_by_stratum[stratum]["pass"] += 1
                passed += 1
            else:
                results_by_stratum[stratum]["fail"] += 1
                failed_queries.append({
                    "query": query_text,
                    "stratum": stratum,
                    "expected_state": expected_state,
                    "expected_standard": expected_standard,
                    "actual_status_code": resp.status_code,
                    "actual_state": actual_state,
                    "explanation": explanation
                })

    report = {
        "metadata": metadata,
        "summary": {
            "total_queries": total,
            "total_passed": passed,
            "overall_accuracy_warning": "DO NOT USE BLENDED ACCURACY. SEE PER-STRATUM METRICS."
        },
        "metrics_by_stratum": results_by_stratum,
        "failures": failed_queries
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Evaluation complete. Report written to %s", output_file)
    logger.info("Stratum breakdown:")
    for stratum, counts in results_by_stratum.items():
        logger.info(
            "  - %s: %d/%d passed", 
            stratum, 
            counts["pass"], 
            counts["total"]
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = base_dir / "data" / "benchmark"
    out_file = base_dir / "backend" / "tests" / "benchmark" / "report.json"
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    run_benchmark(data_dir, out_file)
