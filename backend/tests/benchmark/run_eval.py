"""
Evaluation benchmark runner for the 120-query stratified dataset.

Enforces frozen evaluation by verifying version numbers.
Executes queries via the real API layer (FastAPI TestClient) to exercise
the complete intent classification, entity extraction, and reasoning paths.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, cast

import asyncio
import httpx
from httpx import ASGITransport

from app.main import app

logger = logging.getLogger(__name__)


IDENTIFIER_RE = re.compile(r"\b(?:IS\s*-?\s*\d{2,6}(?::\d{4})?|QCO[-\s]?[A-Z0-9/-]+)\b", re.IGNORECASE)


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


def _new_metric_bucket() -> dict[str, int]:
    return {"total": 0, "pass": 0, "fail": 0}


def _update_metric(bucket: dict[str, int], passed: bool) -> None:
    bucket["total"] += 1
    bucket["pass" if passed else "fail"] += 1


def _normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value).upper().replace("-", " ")).strip()


def _identifier_match(actual: Any, expected: Any) -> bool:
    if expected is None:
        return True
    return _normalize_identifier(actual) == _normalize_identifier(expected)


def _contains_forbidden_identifier(body: dict[str, Any], forbidden: list[str]) -> bool:
    if not forbidden:
        return False

    forbidden_normalized = {_normalize_identifier(item) for item in forbidden}
    text_parts: list[str] = [str(body.get("explanation") or "")]

    decision = body.get("decision") or {}
    for key in ("standard", "basis"):
        if decision.get(key):
            text_parts.append(str(decision[key]))

    for item in body.get("evidence") or []:
        text_parts.append(str(item.get("source_id") or ""))
        text_parts.append(str(item.get("content") or ""))

    found = {_normalize_identifier(match.group(0)) for match in IDENTIFIER_RE.finditer("\n".join(text_parts))}
    return bool(forbidden_normalized.intersection(found))


def _applicable_checks(record: dict[str, Any]) -> dict[str, bool]:
    return {
        "state": True,
        "decision": any(
            record.get(key) is not None
            for key in (
                "expected_standard",
                "expected_mandatory",
                "expected_basis",
                "expected_confidence",
            )
        ),
        "handoff": record.get("expected_handoff_action_type") is not None,
        "citation": int(record.get("min_authoritative_evidence", 0)) > 0,
        "hallucination": bool(record.get("forbidden_identifiers", [])),
    }


def evaluate_record(record: dict[str, Any], resp: Any) -> dict[str, Any]:
    expected_state = record.get("expected_state")
    expected_standard = record.get("expected_standard")
    expected_mandatory = record.get("expected_mandatory")
    expected_basis = record.get("expected_basis")
    expected_confidence = record.get("expected_confidence")
    expected_handoff_action_type = record.get("expected_handoff_action_type")
    min_authoritative_evidence = int(record.get("min_authoritative_evidence", 0))
    forbidden_identifiers = list(record.get("forbidden_identifiers", []))

    actual_status_code = resp.status_code
    body: dict[str, Any] = resp.json() if actual_status_code == 200 else {}
    decision = body.get("decision") or {}
    evidence = body.get("evidence") or []

    state_match = actual_status_code == 200 and body.get("state") == expected_state
    
    # Issue 17 / 26: check structured standard rather than string search
    standard_match = _identifier_match(decision.get("standard"), expected_standard)
    basis_match = _identifier_match(decision.get("basis"), expected_basis)
    mandatory_match = expected_mandatory is None or decision.get("mandatory") == expected_mandatory
    confidence_match = expected_confidence is None or decision.get("confidence") == expected_confidence
    handoff_match = (
        expected_handoff_action_type is None
        or body.get("handoff_action_type") == expected_handoff_action_type
    )
    authoritative_evidence_count = sum(1 for item in evidence if item.get("authoritative") is True)
    citation_match = authoritative_evidence_count >= min_authoritative_evidence
    hallucination_match = not _contains_forbidden_identifier(body, forbidden_identifiers)

    checks = {
        "state": state_match,
        "decision": standard_match and basis_match and mandatory_match and confidence_match,
        "handoff": handoff_match,
        "citation": citation_match,
        "hallucination": hallucination_match,
    }
    applicable_checks = _applicable_checks(record)

    return {
        "passed": all(result for check, result in checks.items() if applicable_checks[check]),
        "checks": checks,
        "applicable_checks": applicable_checks,
        "failure_type": _failure_type(checks, expected_state),
        "actual_status_code": actual_status_code,
        "actual_state": body.get("state"),
        "actual_decision": decision or None,
        "actual_handoff_action_type": body.get("handoff_action_type"),
        "authoritative_evidence_count": authoritative_evidence_count,
        "explanation": body.get("explanation"),
    }


def _failure_type(checks: dict[str, bool], expected_state: str | None) -> str | None:
    if all(checks.values()):
        return None
    if not checks["state"]:
        return "abstention_or_routing_failure" if expected_state in {"CLARIFICATION", "CONFLICT", "NOT_FOUND", "HANDOFF"} else "retrieval_or_routing_failure"
    if not checks["decision"]:
        return "reasoning_failure"
    if not checks["handoff"]:
        return "action_handoff_failure"
    if not checks["citation"]:
        return "citation_failure"
    if not checks["hallucination"]:
        return "generation_failure"
    return "unknown_failure"


def run_benchmark(data_dir: Path, output_file: Path) -> None:
    metadata = load_metadata(data_dir)
    frozen_version = metadata.get("benchmark_version")

    queries_path = data_dir / "eval_queries.jsonl"
    if not queries_path.exists():
        logger.error(f"Benchmark file {queries_path} not found.")
        sys.exit(1)

    # Use ASGITransport to test FastAPI properly without ThreadPool errors
    transport = ASGITransport(app=app)
    
    async def _run() -> tuple[dict[str, Any], dict[str, dict[str, int]]]:
        results_by_stratum: dict[str, dict[str, int]] = {}
        metrics_by_task: dict[str, dict[str, int]] = {
            "state_accuracy": _new_metric_bucket(),
            "decision_correctness": _new_metric_bucket(),
            "citation_completeness": _new_metric_bucket(),
            "official_handoff": _new_metric_bucket(),
            "hallucination_guard": _new_metric_bucket(),
        }
        failure_decomposition: dict[str, int] = {}
        failed_queries: list[dict[str, Any]] = []
        
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
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
        
                    if stratum not in results_by_stratum:
                        results_by_stratum[stratum] = _new_metric_bucket()
        
                    results_by_stratum[stratum]["total"] += 1
                    total += 1
        
                    # Execute query through orchestration
                    resp = await client.post("/query", json={"query": query_text})
                    evaluation = evaluate_record(record, resp)
        
                    _update_metric(metrics_by_task["state_accuracy"], evaluation["checks"]["state"])
                    if evaluation["applicable_checks"]["decision"]:
                        _update_metric(metrics_by_task["decision_correctness"], evaluation["checks"]["decision"])
                    if evaluation["applicable_checks"]["citation"]:
                        _update_metric(metrics_by_task["citation_completeness"], evaluation["checks"]["citation"])
                    if evaluation["applicable_checks"]["handoff"]:
                        _update_metric(metrics_by_task["official_handoff"], evaluation["checks"]["handoff"])
                    if evaluation["applicable_checks"]["hallucination"]:
                        _update_metric(metrics_by_task["hallucination_guard"], evaluation["checks"]["hallucination"])
        
                    if evaluation["passed"]:
                        results_by_stratum[stratum]["pass"] += 1
                        passed += 1
                    else:
                        results_by_stratum[stratum]["fail"] += 1
                        failure_type = evaluation["failure_type"] or "unknown_failure"
                        failure_decomposition[failure_type] = failure_decomposition.get(failure_type, 0) + 1
                        failed_queries.append({
                            "query": query_text,
                            "stratum": stratum,
                            "expected": {
                                "state": record.get("expected_state"),
                                "standard": record.get("expected_standard"),
                                "mandatory": record.get("expected_mandatory"),
                                "basis": record.get("expected_basis"),
                                "confidence": record.get("expected_confidence"),
                                "handoff_action_type": record.get("expected_handoff_action_type"),
                                "min_authoritative_evidence": record.get("min_authoritative_evidence", 0),
                            },
                            "actual": {
                                "status_code": evaluation["actual_status_code"],
                                "state": evaluation["actual_state"],
                                "decision": evaluation["actual_decision"],
                                "handoff_action_type": evaluation["actual_handoff_action_type"],
                                "authoritative_evidence_count": evaluation["authoritative_evidence_count"],
                                "explanation": evaluation["explanation"],
                            },
                            "checks": evaluation["checks"],
                            "applicable_checks": evaluation["applicable_checks"],
                            "failure_type": failure_type,
                        })
            
            report = {
                "metadata": metadata,
                "summary": {
                    "total_queries": total,
                    "total_passed": passed,
                    "overall_accuracy_warning": "DO NOT USE BLENDED ACCURACY. SEE PER-STRATUM METRICS."
                },
                "metrics_by_stratum": results_by_stratum,
                "metrics_by_task": metrics_by_task,
                "failure_decomposition": failure_decomposition,
                "failures": failed_queries
            }
        
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
                
            return report, results_by_stratum

    report, results_by_stratum = asyncio.run(_run())

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
